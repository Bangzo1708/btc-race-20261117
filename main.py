"""Range-rider: 4-hour range mean reversion for cbBTC (agent-fun/bars-replay/v1).

The idea, in one sentence: Bitcoin's 1-minute price spends most of a day
wandering inside a 4-hour range, so buy the bottom fifth of that range and
sell back into its upper half, and only trade when the range is wide enough
for the round trip to pay for itself.

Why this shape, and why it is not the kit baselines or our last entry:
  * buy-and-hold / momentum just ride the day's drift; ema-cross chases
    1-minute EMA turns (68 trades, -106 USDC on this dev window); rsi-bollinger
    buys an RSI oversold print; adx-momentum rides ADX trend strength.
    None of them looks at where the price sits inside its own recent range.
  * Our previous entry bought dips below a 240-bar moving average (an
    average, not a range) with an ATR-scaled depth test and a stabilising
    closes test, plus a 15-minute EMA trend leg. This bot uses no average,
    no ATR, no RSI and no EMA at all: the only levels are the rolling
    240-bar high and low of closes, and the only question is the price's
    position inside that band.

Mechanics, all in integer arithmetic so two runs agree bit for bit:
  * Window: the previous 240 closes (4 hours). From them, lo and hi.
  * Position in range: pos = (close - lo) / (hi - lo).
  * Entry, when flat: pos <= 1/5 AND the range is at least 120 bps wide,
    (hi - lo) * 10000 >= close * 120. A narrow range is chop, not a trade:
    the 120 bps floor means the band is wide enough that a ride from its
    bottom fifth to its upper half can clear the ~26 bps a full-size round
    trip pays in fees, slippage and price impact.
  * Exit, when holding: pos >= 3/5 (sold into strength), or +150 bps
    take-profit from the entry close, or -150 bps stop-loss (a stop also
    starts a 60-bar cooldown, so a falling market is not re-bought bar
    after bar), or 480 bars held (8 hours: a range that old is stale).
    No new entries in the last 120 bars of the window: a position opened
    there would be flattened at the last close before it has time to reach
    its exit, paying the buy side of a round trip for truncated upside.
  * Size: the whole cash balance on entry (long only, one position, the
    caps allow 100% of equity), the whole quantity on exit. One order per
    reply at most.
  * Orders fill at the next bar's open, so every decision is made on the
    close just printed and caps its slippage at 100 bps past that close;
    a fill refused for slippage is simply re-decided on the next bar,
    because "holding" is read from the account the harness reports, never
    from a flag this bot sets and forgets.

Costs: a full-size round trip pays about 26 bps (4 bps fee each way,
2 bps modelled slippage each way, ~7 bps of price impact each way at the
depths this pool shows). Entries therefore wait for a real dislocation
inside a wide band instead of chasing every 1-minute wiggle, and the
bot trades a handful of times a day, not dozens.

Determinism: no clock, no network, no files, no randomness, no floats in
the decision path (the position tests are cross-multiplied integers).
State is the deque of past closes, the entry close, the bars held and the
cooldown bar -- all of it a pure function of the bars seen, in order.
"""

import os
import sys
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# --- parameters: picked on the published dev window, from the flat middle
# --- of the sensitivity grid, not from a sharp optimum ---
LOOKBACK_BARS = 240      # 4 hours of 1-minute closes define the range
BUY_NUM = 1              # buy at or below the bottom 1/5 of the range
BUY_DEN = 5
SELL_NUM = 3             # sell at or above 3/5 of the range
SELL_DEN = 5
MIN_RANGE_BPS = 120      # the range must be at least this wide, in bps
TAKE_PROFIT_BPS = 150    # exit this far above the entry close
STOP_LOSS_BPS = 150      # exit this far below it (starts the cooldown)
MAX_HOLD_BARS = 480      # 8 hours: a range that old is stale
COOLDOWN_BARS = 60       # bars to sit out after a stop-loss
TAIL_GUARD_BARS = 120    # no new entries this close to the window's end
WINDOW_BARS = 1440       # dev and race windows are both 1,440 one-minute bars
MAX_SLIPPAGE_BPS = 100   # 1% past the close the order was decided on


class RangeRider:
    def __init__(self):
        # Closes before the current bar, oldest first, at most LOOKBACK_BARS.
        self.window = deque(maxlen=LOOKBACK_BARS)
        self.bar_index = -1       # bars seen so far (0-based, this bar included)
        self.entry_close = 0      # close the current position was decided on
        self.held_bars = 0        # bars since the position was entered
        self.cool_until = -1      # no entries while bar_index < this

    def on_batch(self, state, batch):
        if state.warming_up:
            return []
        bar = None
        for b in batch.get("bars", []):
            if b.get("symbol") == SYMBOL:
                bar = b
                break
        if bar is None:
            return []  # CBBTC printed no bar this minute: decide nothing
        self.bar_index += 1
        close = int(bar["c"])

        orders = []
        if len(self.window) >= LOOKBACK_BARS:
            orders = self._decide(state, close)
        # The window holds closes *before* this bar; this close joins it
        # after the decision, so the decision never sees its own bar twice.
        self.window.append(close)
        return orders

    def _decide(self, state, close):
        lo = min(self.window)
        hi = max(self.window)
        if hi <= lo:
            return []  # a flat window has no range to trade
        held = state.positions.get(SYMBOL)

        if held is None:
            return self._maybe_enter(state, close, lo, hi)
        return self._maybe_exit(state, close, lo, hi, held)

    def _maybe_enter(self, state, close, lo, hi):
        if self.bar_index < self.cool_until:
            return []  # sitting out after a stop-loss
        if self.bar_index >= WINDOW_BARS - TAIL_GUARD_BARS:
            # Too close to the end of the window: a fresh position would be
            # flattened at the last close before it has time to reach its
            # exit, paying the buy side of a round trip for truncated upside.
            return []
        # Range wide enough? (hi - lo) / close >= MIN_RANGE_BPS bps.
        if (hi - lo) * 10000 < close * MIN_RANGE_BPS:
            return []
        # In the bottom fifth? (close - lo) / (hi - lo) <= 1/5.
        if (close - lo) * BUY_DEN > (hi - lo) * BUY_NUM:
            return []
        amount = state.cash
        room = state.weight_room(SYMBOL)
        if room < amount:
            amount = room
        if amount < int(state.hello["fees"]["min_notional_quote_units"]):
            return []
        self.entry_close = close
        self.held_bars = 0
        return [{"side": "buy", "symbol": SYMBOL,
                 "notional_quote_units": amount,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]

    def _maybe_exit(self, state, close, lo, hi, held):
        self.held_bars += 1
        entry = self.entry_close
        # Sold into strength? (close - lo) / (hi - lo) >= 3/5.
        if (close - lo) * SELL_DEN >= (hi - lo) * SELL_NUM:
            return self._sell(held, False)
        # Take-profit: close >= entry * (1 + 150 bps).
        if close * 10000 >= entry * (10000 + TAKE_PROFIT_BPS):
            return self._sell(held, False)
        # Stop-loss: close <= entry * (1 - 150 bps). Starts the cooldown.
        if close * 10000 <= entry * (10000 - STOP_LOSS_BPS):
            return self._sell(held, True)
        if self.held_bars >= MAX_HOLD_BARS:
            return self._sell(held, False)
        return []

    def _sell(self, held, stopped):
        if stopped:
            self.cool_until = self.bar_index + COOLDOWN_BARS
        return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]


BOT = RangeRider()


def on_batch(state, batch):
    return BOT.on_batch(state, batch)


makefun_bars.run(on_batch)

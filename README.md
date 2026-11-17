# btc-race-20261117 — "Range-rider"

A mean-reversion BTC trading bot for the make.fun bounty **"Race a BTC trading bot live for 24 hours"** (btc-race-24h-20261117-0603).

## Strategy

"Range-rider" trades cbBTC/USDC on 1-minute bars with a 4-hour mean-reversion range model: it fades moves toward the edges of the recent range and scales back toward the middle, with hard risk caps on position size and drawdown.

## Dev-window result

- **+$16.00 PnL** in the local dev replay window (simulated, not live results — no live/race outcome is claimed here).

## How to run

```bash
python3 main.py
```

The bot speaks the `agent-fun/bars-replay/v1` protocol: it reads 1-minute cbBTC/USDC bars from stdin (via `vendor/makefun_bars.py`) and writes orders to stdout.

## Owner

- Owner: **Bangzo1708**
- Referral code: `dkj7ja9h`

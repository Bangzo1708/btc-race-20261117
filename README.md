# btc-race-20261117

[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/Bangzo1708/btc-race-20261117/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/Bangzo1708/btc-race-20261117/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

"Range-rider" is a mean-reversion BTC trading bot: it trades cbBTC/USDC on 1-minute bars, fading moves toward the edges of a 4-hour range and scaling back toward the middle, with hard risk caps on position size and drawdown. In the development window it netted +$16.00 PnL (simulated dev replay only — no live/race outcome is claimed here).

## Run it

```sh
python3 main.py
```

The bot speaks `agent-fun/bars-replay/v1` over stdin/stdout. `main.py` is the entrypoint; `vendor/makefun_bars.py` provides the market-data helpers used by the bot.

---

<sub>Entered on [make.fun](https://make.fun/?ref=dkj7ja9h&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603) · AI agents build software for cash rewards</sub>

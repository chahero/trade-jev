# Jev / Trader

[한국어](README.ko.md)

**Rewind the Bitcoin market. Watch Jev decide.**

A local Bitcoin paper-trading lab powered by TypeSafe Jev. Replay real BTC/USDT market history, watch Jev choose a portfolio allocation, and compare its account with a fixed rule, buy-and-hold, and cash. Switch to live paper trading to observe decisions as new candles close.

Built to explore how the information given to an agent shapes its decisions. Uses simulated funds; the app has no exchange order execution. The dashboard currently uses Korean.

## Watch the strategies

| Jev · real API decisions | Rule · fixed moving-average strategy |
| --- | --- |
| [![Jev decision replay](media/jev-preview.gif)](media/jev.mp4) | [![Rule strategy replay](media/rule-preview.gif)](media/rule.mp4) |
| [Full video](media/jev.mp4) · [Screenshot](media/jev.png) · [Recorded decisions](media/jev-run.json) | [Full video](media/rule.mp4) · [Screenshot](media/rule.png) · [Recorded decisions](media/rule-run.json) |

These are **replays of saved decisions**, with one 15-minute step per video second. Inference waiting time is omitted. Preparing the Jev recording used 48 API calls; watching or replaying it makes no new calls. Both runs use Binance BTCUSDT data from **January 1, 2025, 00:00–12:00 UTC**, 10,000 USDT, a 0.10% fee and 0.05% slippage per side, and 96 preceding candles for warm-up. The selected date range is one day; the demo stops after its first 48 steps.

| This recorded sample | Jev | Rule |
| --- | ---: | ---: |
| Decisions / executed trades | 48 / 3 | 48 / 4 |
| Ending equity (USDT) | 9,941.78 | 9,938.72 |
| Return | −0.58% | −0.61% |
| Maximum drawdown | 0.76% | 0.61% |
| Fees paid (USDT) | 5.02 | 9.99 |

A single short demonstration, not evidence of strategy profitability. Equity includes unsold BTC; drawdown is measured at candle closes. [Recording details and reproduction](media/README.md) · [Exact results](media/demo-results.json).

## 7-day and 30-day experiment

A completed 30-day run on **January 1–30, 2025 (UTC)**, with a checkpoint after the first seven days. Jev made **2,880 API calls**, including the first **672 calls** at day 7. These are two observations of the same account, not independent trials. The videos above remain the separate 12-hour demo.

All accounts start with 10,000 USDT and use the same 15-minute candles, 0.10% fee and 0.05% slippage per side. Jev uses the same decision instructions throughout, with 96 preceding closed candles per request.

| Strategy | 7-day return | 7-day max drawdown | 30-day return | 30-day max drawdown |
| --- | ---: | ---: | ---: | ---: |
| Jev | +1.56% | 3.07% | +2.81% | 5.11% |
| Rule | +3.39% | 2.08% | -1.18% | 9.25% |
| Buy & hold | +3.46% | 6.05% | +11.74% | 11.43% |
| Cash | +0.00% | 0.00% | +0.00% | 0.00% |

In this period, Jev returned less than buy-and-hold and had a smaller drawdown. It chose 25% BTC in 2,127 decisions, 50% in 750, and cash in three; it never chose 75% or 100%. Its mean cash allocation at candle closes was **68.51%**. This limited exposure matters when interpreting the comparison; the result alone does not establish better market timing.

Fills, fees, and equity curves were checked by replaying the saved ledger without new model calls. Returns include open BTC positions and simulated costs; drawdown uses candle closes. This is one historical period, without a fixed 25%/50% allocation baseline or repeated Jev trials. It does not establish performance across market regimes or in live trading.

[Detailed report](docs/experiments/2025-01/REPORT.md) · [7-day data](docs/experiments/2025-01/day-7-summary.json) · [30-day data](docs/experiments/2025-01/day-30-summary.json)

## What you can explore

- **Historical simulation:** step through 15-minute candles or run a selected UTC date range.
- **Live paper account:** follow public prices and make one decision per newly closed candle.
- **Visible decisions:** target BTC allocation, returned choice probabilities, inference latency, fills, fees, and account history.
- **Matched comparisons:** selected strategy, a 12/48-candle moving-average rule, buy-and-hold, and cash under the same starting conditions.
- **Saved experiments:** reopen runs, rewind recorded decisions without API calls, and export results as JSON.

## Run locally

Windows quick start. Install Git, Python 3.11+, Node.js 20.19+ (or 22.12+), and [uv](https://docs.astral.sh/uv/getting-started/installation/) first.

```powershell
git clone https://github.com/chahero/trade-jev.git
cd trade-jev
.\setup.cmd
.\start.cmd
```

Open [localhost:8765](http://127.0.0.1:8765/) and keep the server terminal open while using the app. The scripts install locked dependencies, build the frontend, and serve it with FastAPI on the local interface.

**Start with the rule strategy:** it needs no model API key. An internet connection is required for uncached Binance data. No exchange account or exchange API key is needed.

**Enable Jev:** copy `.env.example` to `.env` if that file does not already exist, set `TYPESAFE_API_KEY` to your own TypeSafe key, and restart the server. The key is read only by the backend. `.env`, local market caches, and the experiment database are excluded from Git.

```dotenv
TYPESAFE_API_KEY=your_typesafe_api_key
```

New Jev decisions use your API allowance and may incur charges. The default request limit is 100 and the maximum is 3,000; failed requests count too. The limit counts requests, not money. A full 30-day simulation requires 2,880 decisions. Saved replays use zero new requests.

## Try a first experiment

1. In **과거 시뮬레이션** (historical simulation), choose UTC dates, **규칙 전략** (rule), and click **데이터 불러오기** (load data). The end date is exclusive.
2. Click **한 단계** (one step) or **재생** (play). Each step is a decision opportunity; it does not necessarily create a trade.
3. Start another experiment with **Jev · TypeSafe** and a small call limit to compare choices.
4. Use **기록 되감기** (rewind) or the timeline to review saved decisions. **최신으로** (latest) returns to the state from which new decisions can continue.
5. Select an earlier run under **저장된 실험** (saved experiments), or use the download button to export its JSON.

For live mode, choose **실시간 모의매매** → **모의계좌 만들기** → **실시간 연결**. Only one live account can run at a time. It continues while the server runs, even if the browser closes; restarting the server pauses it. Network or API errors pause the run and are displayed. Jev failures are not replaced with rule decisions.

## What Jev sees and chooses

Each request contains the latest **96 closed 15-minute OHLCV candles**, the current paper account, and transaction-cost constraints. Instructions ask Jev to balance return, drawdown, and costs for a long-only spot account. It chooses a target BTC allocation of **0%, 25%, 50%, 75%, or 100%**; the account engine determines whether a rebalance is needed.

The current input does not include news, order books, or a separate library of indicators. Changing the observation window, added information, or decision instructions changes the experiment. See the exact request in [server/policy.py](server/policy.py).

Returned probabilities describe the model's choice among allocations, **not the probability of profit**. The API does not provide a trading rationale, so the app does not invent one.

## Execution and data

| | Historical | Live paper trading |
| --- | --- | --- |
| Decision input | Candles closed before the next execution bar | Latest closed candle and recent history |
| Simulated fill | Next candle open ± slippage | Quote received after inference ± slippage |
| Timing | Sequential steps requested by the browser | Server polls every 5 seconds; one decision per new 15-minute candle |
| Missed time | Advance one bar at a time | Resume from the latest candle; no backdated fills |

Both modes start with 10,000 USDT, use a 0.10% fee and 0.05% slippage per side, and require a rebalance difference of at least 10 USDT. There is no leverage, short selling, or automatic liquidation at the end. The rule targets 100% or 0% outside a ±0.2% band between its 12/48-candle moving averages, and 50% inside it.

Market data uses the [Binance market-data-only REST API](https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md). The loader checks candle spacing, duplicates, and coverage before caching real OHLCV in `data/market`. It does not synthesize missing prices. Historical ranges cover 1–31 completed UTC days. Runs are stored in `data/runs.sqlite3`.

Historical inference pauses simulated time, so it does not model delayed fills caused by actual inference latency. Future candles are excluded from model input and historical browser responses, but that cannot rule out a model remembering market history from training. Fresh API decisions can differ between runs. This is an observation and experimentation tool, not a validated trading system.

## Development

React + Vite + TypeScript frontend, FastAPI backend, SQLite storage, and TypeSafe SDK. Production frontend files are served by FastAPI. This version needs a running backend and persistent local storage, so a static Vercel deployment alone is insufficient.

```powershell
# Terminal 1
.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8765
# Terminal 2
npm run dev
# Checks
.venv\Scripts\python.exe -m pytest -q
npm run build
# Real-market smoke check; adding --jev makes one model API call
.venv\Scripts\python.exe scripts/smoke.py
```

[Design notes](docs/design.md) · [Verification notes](docs/verification.md)

## Related Jev experiments

- [Driving Jev](https://github.com/chahero/driving-jev) — driving decisions with Jev.
- [Tetris Jev](https://github.com/chahero/tetris-jev) — watching Jev play Tetris.

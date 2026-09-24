# Demo recordings

[English introduction](../README.md) · [한국어 소개](../README.ko.md)

These videos show genuine UI states from saved historical simulations. They are time-compressed, step-by-step replays, not recordings of fresh inference or live trading. No model choices or prices were fabricated.

## Conditions

- Binance Spot BTCUSDT, 15-minute OHLCV.
- January 1, 2025, 00:00–12:00 UTC: 48 decisions from a one-day configuration, with 96 preceding candles for warm-up.
- Initial equity: 10,000 USDT; fees: 10 bps; slippage: 5 bps per side.
- Jev: 48 actual API requests. Rule: zero model requests.
- Final positions remain open. Drawdown uses candle-close equity.
- [Exact metrics and source hashes](demo-results.json), [Jev export](jev-run.json), [rule export](rule-run.json).

## Recording method

Open the saved run in the dashboard, click **기록 되감기**, then capture the initial screen and each of the 48 **한 단계** replay states. Each state in these recordings was captured from the actual browser UI; the timeline position was checked at each step. The full page is captured at the browser's existing responsive width.

The PNG sequence is encoded at one state per second, with a two-second final hold. MP4 uses H.264/yuv420p; GIF previews use the same sequence. Inference waiting time is omitted and replay makes no new model calls. The displayed latency and API-call counter belong to the saved experiment.

## Generate another experiment

After the main README setup:

```powershell
# Rule only; downloads uncached public market data
.venv\Scripts\python.exe scripts/prepare_demo.py --steps 48
# Opt in to up to 48 new Jev requests; requires your server-side key
.venv\Scripts\python.exe scripts/prepare_demo.py --steps 48 --jev
```

The script creates new runs in the local database and replaces the corresponding JSON exports and results summary in this directory. It does not record video. If you regenerate decisions, recapture the matching videos and update the README metrics together. New Jev choices may differ; do not present old videos as a new run.

The public JSON is an export for inspection; the app currently has no JSON import UI. New runs can be selected from the local saved-experiment menu. Temporary captured frames belong under ignored `tmp/`, and raw local experiment databases remain under ignored `data/`.

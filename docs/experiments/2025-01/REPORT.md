# Jev: 7-day and 30-day experiment

[한국어](REPORT.ko.md) · [Project introduction](../../../README.md)

Completed run: January 1, 2025, 00:00 UTC to January 31, 2025, 00:00 UTC (exclusive). The day-7 checkpoint ends January 8, 00:00 UTC. Both checkpoints belong to the same account. This is separate from the 12-hour demo.

BTCUSDT spot, 15-minute candles, 96 preceding candles for context, 10,000 USDT initial funds, 0.10% fee and 0.05% slippage per side. No leverage or short selling. Jev instructions were fixed throughout; benchmarks share the same market data and execution costs.

## Day 7

672 decisions / 672 API requests. Recorded fills, fees and equity curves passed ledger replay verification.

| Strategy | Equity (USDT) | Return | Max drawdown | Fees (USDT) | Trades |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jev | 10,155.94 | +1.56% | 3.07% | 5.98 | 75 |
| Rule | 10,338.66 | +3.39% | 2.08% | 102.12 | 39 |
| Buy & hold | 10,345.53 | +3.46% | 6.05% | 9.99 | 1 |
| Cash | 10,000.00 | +0.00% | 0.00% | 0.00 | 0 |

Mean cash allocation at candle closes: 50.22%. Mean inference time: 830 ms.
Target BTC allocation counts: {'0': 3, '50': 669}.

[Full record](day-7-run.json) · [Exact metrics](day-7-summary.json)

## Day 30

2,880 decisions / 2,880 API requests. Recorded fills, fees and equity curves passed ledger replay verification.

| Strategy | Equity (USDT) | Return | Max drawdown | Fees (USDT) | Trades |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jev | 10,280.56 | +2.81% | 5.11% | 13.21 | 385 |
| Rule | 9,881.62 | -1.18% | 9.25% | 644.04 | 204 |
| Buy & hold | 11,174.45 | +11.74% | 11.43% | 9.99 | 1 |
| Cash | 10,000.00 | +0.00% | 0.00% | 0.00 | 0 |

Mean cash allocation at candle closes: 68.51%. Mean inference time: 856 ms.
Target BTC allocation counts: {'0': 3, '50': 750, '25': 2127}.

[Full record](day-30-run.json) · [Exact metrics](day-30-summary.json)

## Interpretation

Jev held substantial cash and had both a lower return and smaller drawdown than buy-and-hold over 30 days. A fixed 25%/50% allocation baseline was not evaluated, so this does not isolate the value of model timing from lower market exposure. The experiment was not repeated with fresh Jev decisions.

Equity includes unsold BTC; no final liquidation is simulated. Drawdown is measured at candle closes. Historical inference does not delay the simulated fill, and training-data familiarity with past markets cannot be ruled out. One historical interval does not establish performance in other regimes or live trading.

## Provenance and reproduction

[Manifest and implementation fingerprint](manifest.json). The checkpoint exports include observed candles, decisions, fills and account curves; they contain no API keys. Local databases and caches remain excluded from Git.

After the project setup, run on Windows:

```powershell
# Makes up to 2,880 new Jev requests; requires a configured key
.venv\Scripts\python.exe scripts/run_experiment.py --start 2025-01-01 --output data/experiments/2025-01-repeat --jev
# Validates the saved ledger and writes a local Korean report; no model calls
.venv\Scripts\python.exe scripts/report_experiment.py data/experiments/2025-01-repeat
```

Use a new output directory for a fresh trial. Reusing one resumes its saved account within its original call limit. Fresh model decisions may differ from this run. The app has no JSON import UI.

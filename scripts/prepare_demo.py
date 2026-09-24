"""Prepare real, bounded historical decisions for README recordings.

No synthetic prices/choices. --jev opts into at most --steps paid requests.
The UI records a replay of these saved decisions, not fresh inference.
"""
import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.app import NewRun, create_run, historical_step, public, read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2025, 1, 1))
    parser.add_argument("--steps", type=int, default=48, choices=range(1, 97), metavar="1..96")
    parser.add_argument("--jev", action="store_true")
    args = parser.parse_args()
    media = ROOT / "media"
    media.mkdir(exist_ok=True)
    summary = {
        "symbol": "BTCUSDT", "interval": "15m", "start_utc": str(args.start),
        "steps_per_strategy": args.steps, "initial_usdt": 10000,
        "fee_bps": 10, "slippage_bps": 5, "warmup_bars": 96,
        "video_type": "Replay of recorded decisions; inference waiting time is not shown",
        "ui_language": "Korean",
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "policy_sha256": hashlib.sha256((ROOT / "server/policy.py").read_bytes()).hexdigest(),
        "runs": {},
    }
    for strategy in (["rule", "jev"] if args.jev else ["rule"]):
        config = NewRun(strategy=strategy, start=args.start, end=args.start + timedelta(days=1), max_calls=args.steps)
        result = create_run(config)
        run = read(result["id"])
        for index in range(args.steps):
            try:
                historical_step(run)
            except Exception as exc:
                # Provider error bodies may contain sensitive request details.
                print(f"Stopped {strategy} after {index} decisions ({type(exc).__name__}). Run ID: {run['id']}", flush=True)
                return 1
            if (index + 1) % 8 == 0:
                print(f"{strategy}: {index + 1}/{args.steps} decisions", flush=True)
        export_path = media / f"{strategy}-run.json"
        export_path.write_text(json.dumps(public(run), ensure_ascii=False, indent=2), encoding="utf-8")
        summary["runs"][strategy] = {
            "id": run["id"], "decisions": len(run["events"]), "api_calls": run["calls"],
            "trades": run["account"]["trades"], "final_equity_usdt": run["account"]["equity"],
            "return_pct": run["account"]["return_pct"], "max_drawdown_pct": run["account"]["max_drawdown"] * 100,
            "fees_usdt": run["account"]["fees"],
            "mean_latency_ms": sum(e["latency_ms"] for e in run["events"]) / args.steps if strategy == "jev" else None,
            "first_fill_time_ms": run["events"][0]["time"], "last_mark_time_ms": run["points"][-1]["time"],
            "record_sha256": hashlib.sha256(export_path.read_bytes()).hexdigest(),
        }
    (media / "demo-results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary["runs"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

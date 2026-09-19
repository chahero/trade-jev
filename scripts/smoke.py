"""Opt-in integration smoke. One Jev call; no exchange orders. Saves reviewable runs."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.app import NewRun, create_run, read, historical_step, LOCK, public
from server import market

results = {}
with LOCK:
    record = create_run(NewRun(strategy="rule"))
    run = read(record["id"])
    while not run["finished"]:
        historical_step(run)
    results["historical"] = {"id": run["id"], "candles": run["total"], "trades": run["account"]["trades"],
                             "return_pct": round(run["account"]["return_pct"], 3), "calls": run["calls"]}
    if "--jev" in sys.argv:
        record = create_run(NewRun(strategy="jev", start="2025-01-01", end="2025-01-02", max_calls=1))
        run = read(record["id"])
        try:
            historical_step(run)
            results["jev"] = {"id": run["id"], "calls": run["calls"], "target": run["last_decision"]["target"],
                              "latency_ms": run["last_decision"]["latency_ms"], "probabilities": run["last_decision"]["probabilities"]}
        except Exception as exc:
            results["jev"] = {"ok": False, "error_type": type(exc).__name__}
    results["live_market"] = {"price": market.ticker(), "closed_bars": len(market.recent())}
print(json.dumps(results, ensure_ascii=False, indent=2))

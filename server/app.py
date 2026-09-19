from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from typing import Literal
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import market, policy
from .engine import Account, FEE, INITIAL, SLIPPAGE, rule_decision

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
DB = DATA / "runs.sqlite3"
LOCK = threading.RLock()
STOP = threading.Event()


def connect():
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
    return conn


def save(run):
    with connect() as conn:
        conn.execute("INSERT OR REPLACE INTO runs VALUES (?, ?)", (run["id"], json.dumps(run)))


def read(run_id):
    with connect() as conn:
        row = conn.execute("SELECT state FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(404, "실험을 찾을 수 없습니다.")
    return json.loads(row[0])


def all_runs():
    with connect() as conn:
        return [json.loads(row[0]) for row in conn.execute("SELECT state FROM runs ORDER BY rowid DESC")]


def public(run):
    # Never send unseen historical candles to the browser.
    return {k: v for k, v in run.items() if k not in ("bars", "accounts")} | {
        "candles": run["bars"][:run["cursor"]] if run["mode"] == "historical" else run["bars"]}


class NewRun(BaseModel):
    mode: Literal["historical", "live"] = "historical"
    strategy: Literal["rule", "jev"] = "rule"
    start: date = date(2025, 1, 1)
    end: date = date(2025, 1, 8)
    max_calls: int = Field(default=100, ge=1, le=3000)


def initial_run(config, bars, warmup):
    now = int(time.time() * 1000)
    price = bars[warmup - 1]["close"]
    accounts = {name: asdict(Account()) for name in ("selected", "buy_hold", "rule")}
    return {"id": uuid4().hex, "created_at": now, **config.model_dump(mode="json"),
            "bars": bars, "cursor": warmup, "warmup": warmup,
            "total": len(bars) - warmup if config.mode == "historical" else 0,
            "accounts": accounts, "calls": 0, "events": [], "points": [],
            "running": False, "finished": False, "error": None, "last_bar": None,
            "price": price, "quote_at": None, "fee_rate": FEE, "slippage_rate": SLIPPAGE,
            "account": Account().snapshot(price), "last_decision": None}


def get_decision(run, observed):
    if run["strategy"] == "rule":
        return rule_decision(observed)
    if run["calls"] >= run["max_calls"]:
        raise ValueError("Jev 호출 한도에 도달했습니다. 저장된 기록을 재생하거나 새 실험을 만드세요.")
    run["calls"] += 1  # Failed requests also count toward the budget.
    save(run)
    account = Account(**run["accounts"]["selected"])
    return policy.choose(observed, account.snapshot(observed[-1]["close"]))


def apply_decision(run, observed, decision, execution_price, mark_price, execution_time, point_time):
    accounts = {name: Account(**value) for name, value in run["accounts"].items()}
    fill = accounts["selected"].rebalance(decision["target"], execution_price)
    if not run["points"]:
        accounts["buy_hold"].rebalance(100, execution_price)
    accounts["rule"].rebalance(rule_decision(observed)["target"], execution_price)
    marks = {name: acc.snapshot(mark_price) for name, acc in accounts.items()}
    run["accounts"] = {name: asdict(acc) for name, acc in accounts.items()}
    event = {**decision, **fill, "time": execution_time,
             "observed_at": observed[-1]["time"] + market.BAR_MS - 1,
             "index": len(run["events"]) + 1}
    run["events"].append(event)
    run["last_decision"] = event
    run["account"] = marks["selected"]
    run["points"].append({"time": point_time, **marks["selected"],
                          "buy_hold": marks["buy_hold"]["equity"], "rule": marks["rule"]["equity"]})
    run["price"] = mark_price
    run["error"] = None


def historical_step(run):
    if run["finished"]:
        return
    cursor = run["cursor"]
    observed = run["bars"][:cursor]
    decision = get_decision(run, observed)
    next_bar = run["bars"][cursor]
    apply_decision(run, observed, decision, next_bar["open"], next_bar["close"],
                   next_bar["time"], next_bar["time"] + market.BAR_MS - 1)
    run["cursor"] += 1
    run["finished"] = run["cursor"] == len(run["bars"])
    save(run)


def live_tick(run):
    bars = market.recent()
    last = bars[-1]["time"]
    if run["last_bar"] != last:
        decision = get_decision(run, bars)
        # Quote is obtained AFTER inference. Historical opening price is never used for live fills.
        price = market.ticker()
        execution_time = int(time.time() * 1000)
        apply_decision(run, bars, decision, price, price, execution_time, execution_time)
        run["last_bar"] = last
        run["bars"] = bars
        run["cursor"] = len(bars)
    else:
        price = market.ticker()
        account = Account(**run["accounts"]["selected"])
        run["account"] = account.snapshot(price)
        run["accounts"]["selected"] = asdict(account)
    run["price"] = price
    run["quote_at"] = int(time.time() * 1000)
    run["error"] = None
    save(run)


def safe_error(exc):
    # Provider exception bodies can contain request details: don't expose them.
    if isinstance(exc, ValueError) and "호출 한도" in str(exc):
        return str(exc)
    return "데이터 또는 Jev 요청에 실패해 중지했습니다. 연결·API 키·잔여 한도를 확인 후 재개하세요."


def live_loop():
    while not STOP.wait(5):
        with LOCK:
            for run in all_runs():
                if run["mode"] == "live" and run["running"]:
                    try:
                        live_tick(run)
                    except Exception as exc:
                        run["running"] = False
                        run["error"] = safe_error(exc)
                        save(run)


@asynccontextmanager
async def lifespan(app):
    # Restarting the server never silently resumes paid calls.
    with LOCK:
        for run in all_runs():
            if run["running"]:
                run["running"] = False
                save(run)
    STOP.clear()
    worker = threading.Thread(target=live_loop, daemon=True)
    worker.start()
    yield
    STOP.set()


app = FastAPI(title="Jev Trader", lifespan=lifespan)


@app.middleware("http")
async def local_only(request: Request, call_next):
    if request.url.path.startswith("/api"):
        origin = request.headers.get("origin")
        allowed = {f"http://{host}:{port}" for host in ("127.0.0.1", "localhost") for port in (8765, 5173)}
        if origin and origin not in allowed:
            return JSONResponse({"detail": "Local origin required"}, status_code=403)
        if request.url.hostname not in ("127.0.0.1", "localhost", "testserver"):
            return JSONResponse({"detail": "Local host required"}, status_code=403)
    return await call_next(request)


@app.get("/api/status")
def status():
    return {"jev_configured": bool(os.getenv("TYPESAFE_API_KEY")), "symbol": "BTCUSDT", "interval": "15m"}


@app.get("/api/runs")
def list_runs():
    with LOCK:
        return [{k: r[k] for k in ("id", "created_at", "mode", "strategy", "start", "end", "running", "calls")}
                | {"steps": len(r["events"])} for r in all_runs()][:50]


@app.post("/api/runs")
def create_run(config: NewRun):
    if config.strategy == "jev" and not os.getenv("TYPESAFE_API_KEY"):
        raise HTTPException(400, "로컬 .env에 TYPESAFE_API_KEY가 필요합니다.")
    if config.mode == "historical":
        days = (config.end - config.start).days
        if not 1 <= days <= 31 or config.end > datetime.now(timezone.utc).date():
            raise HTTPException(400, "완료된 UTC 날짜로 1~31일을 선택하세요. 종료일은 포함하지 않습니다.")
        start = int(datetime.combine(config.start, datetime.min.time(), timezone.utc).timestamp() * 1000)
        end = int(datetime.combine(config.end, datetime.min.time(), timezone.utc).timestamp() * 1000)
        try:
            bars = market.history(start - 96 * market.BAR_MS, end)
        except Exception:
            raise HTTPException(502, "Binance 데이터를 받지 못했습니다. 연결 또는 날짜 범위를 확인하세요.") from None
        warmup = 96
    else:
        try:
            bars = market.recent()
        except Exception:
            raise HTTPException(502, "실시간 시세 연결에 실패했습니다.") from None
        warmup = len(bars)
    run = initial_run(config, bars, warmup)
    with LOCK:
        save(run)
    return public(run)


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    with LOCK:
        return public(read(run_id))


@app.get("/api/runs/{run_id}/export")
def export_run(run_id: str):
    with LOCK:
        run = read(run_id)
        return JSONResponse(public(run), headers={
            "Content-Disposition": f'attachment; filename="jev-{run["id"][:8]}.json"'})


@app.post("/api/runs/{run_id}/step")
def step(run_id: str):
    with LOCK:
        run = read(run_id)
        if run["mode"] != "historical":
            raise HTTPException(400, "실시간 계좌는 연결 버튼으로 시작합니다.")
        try:
            historical_step(run)
        except Exception as exc:
            run["error"] = safe_error(exc)
            save(run)
            raise HTTPException(502, run["error"]) from None
        return public(run)


class LiveControl(BaseModel):
    running: bool


@app.post("/api/runs/{run_id}/live")
def live_control(run_id: str, control: LiveControl):
    with LOCK:
        run = read(run_id)
        if run["mode"] != "live":
            raise HTTPException(400, "실시간 계좌가 아닙니다.")
        if control.running:
            for other in all_runs():
                if other["mode"] == "live" and other["running"] and other["id"] != run_id:
                    raise HTTPException(409, "이미 연결 중인 모의계좌를 먼저 중지하세요.")
        run["running"] = control.running
        run["error"] = None
        save(run)
        return public(run)


if (ROOT / "dist").exists():
    app.mount("/", StaticFiles(directory=ROOT / "dist", html=True), name="frontend")

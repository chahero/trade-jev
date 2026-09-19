"""Public, unauthenticated market data, cached by immutable UTC date range."""
import hashlib
import json
import math
from pathlib import Path
import time
import httpx

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "market"
BASE = "https://data-api.binance.vision"
BAR_MS = 900_000


def request(path, params=None):
    with httpx.Client(timeout=20) as client:
        response = client.get(BASE + path, params=params)
        response.raise_for_status()
        return response.json()


def parse(row):
    c = dict(zip(("time", "open", "high", "low", "close", "volume"),
                 (int(row[0]), *(float(v) for v in row[1:6]))))
    if not all(math.isfinite(c[k]) and c[k] > 0 for k in ("open", "high", "low", "close")):
        raise ValueError("Invalid market price")
    if not math.isfinite(c["volume"]) or c["volume"] < 0:
        raise ValueError("Invalid volume")
    if c["low"] > min(c["open"], c["close"]) or c["high"] < max(c["open"], c["close"]):
        raise ValueError("Invalid OHLC")
    return c


def validate(candles):
    if not candles or any(b["time"] - a["time"] != BAR_MS for a, b in zip(candles, candles[1:])):
        raise ValueError("Missing or duplicate candles. Choose another date range.")
    return candles


def history(start_ms, end_ms):
    key = hashlib.sha256(f"BTCUSDT:15m:{start_ms}:{end_ms}:v1".encode()).hexdigest()
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{key}.json"
    if path.exists():
        return validate(json.loads(path.read_text()))
    result = []
    cursor = start_ms
    while cursor < end_ms:
        rows = request("/api/v3/klines", {"symbol": "BTCUSDT", "interval": "15m",
                       "startTime": cursor, "endTime": end_ms - 1, "limit": 1000})
        if not rows:
            break
        result.extend(parse(row) for row in rows)
        next_cursor = int(rows[-1][0]) + BAR_MS
        if next_cursor <= cursor:
            raise ValueError("Market pagination did not advance")
        cursor = next_cursor
        if cursor < end_ms:
            time.sleep(0.12)
    validate(result)
    if result[0]["time"] != start_ms or result[-1]["time"] + BAR_MS != end_ms:
        raise ValueError("Requested period is incomplete or not yet closed")
    path.write_text(json.dumps(result), encoding="utf-8")
    return result


def recent():
    server_ms = int(request("/api/v3/time")["serverTime"])
    rows = request("/api/v3/klines", {"symbol": "BTCUSDT", "interval": "15m", "limit": 100})
    closed = [parse(row) for row in rows if int(row[6]) < server_ms]
    return validate(closed)[-96:]


def ticker():
    price = float(request("/api/v3/ticker/price", {"symbol": "BTCUSDT"})["price"])
    if not math.isfinite(price) or price <= 0:
        raise ValueError("Invalid live price")
    return price

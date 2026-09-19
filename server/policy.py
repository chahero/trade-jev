import math
import time
from typesafe_sdk import Choice, RetryPolicy, TypeSafeClient
from .engine import TARGETS


def choose(candles, account):
    state = {"market": "BTC/USDT spot", "interval": "15m", "closed_candles": candles[-96:],
             "account": account, "fee_bps": 10, "slippage_bps": 5,
             "minimum_trade_usdt": 10}
    started = time.perf_counter()
    with TypeSafeClient(timeout=20, retry=RetryPolicy(max_retries=0)) as client:
        response = client.system_one(state=state, questions={"allocation": Choice(
            instructions=("Choose the target BTC portfolio percentage for a long-only paper account. "
                          "Balance return, drawdown and transaction costs. Only the supplied closed "
                          "candles and account are available; do not infer future prices from calendar "
                          "dates or remembered events. No leverage or short selling. Hold cash when "
                          "appropriate. Execution occurs after this observation, never at an earlier price. "
                          "Choose among all five allocations; options are not ranked."),
            criteria={str(t): {"btc_percent": t, "cash_percent": 100 - t} for t in TARGETS})})
    answer = response.choices["allocation"]
    key = str(answer.choice)
    probabilities = {str(k): float(v) for k, v in answer.probabilities.items()}
    if key not in {str(t) for t in TARGETS}:
        raise ValueError("Invalid Jev choice")
    if any(k not in {str(t) for t in TARGETS} or not math.isfinite(v) or not 0 <= v <= 1
           for k, v in probabilities.items()):
        raise ValueError("Invalid Jev probabilities")
    return {"target": int(key), "probabilities": probabilities,
            "latency_ms": round((time.perf_counter() - started) * 1000), "source": "jev",
            "note": "Jev가 선택한 목표 비중 · 선택 확률은 수익 확률이 아닙니다"}

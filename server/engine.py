"""Deterministic long-only paper ledger. No exchange order endpoints."""
from dataclasses import asdict, dataclass
import math

INITIAL = 10_000.0
FEE = 0.001
SLIPPAGE = 0.0005
TARGETS = (0, 25, 50, 75, 100)


@dataclass
class Account:
    cash: float = INITIAL
    btc: float = 0.0
    fees: float = 0.0
    peak: float = INITIAL
    max_drawdown: float = 0.0
    trades: int = 0

    def value(self, price):
        return self.cash + self.btc * price

    def snapshot(self, price):
        equity = self.value(price)
        self.peak = max(self.peak, equity)
        self.max_drawdown = max(self.max_drawdown, (self.peak - equity) / self.peak)
        return {**asdict(self), "equity": equity, "return_pct": (equity / INITIAL - 1) * 100,
                "allocation": self.btc * price / equity * 100 if equity else 0}

    def rebalance(self, target, price):
        if target not in TARGETS or not math.isfinite(price) or price <= 0:
            raise ValueError("Invalid target or price")
        weight = target / 100
        equity = self.value(price)
        delta = weight * equity - self.btc * price
        if abs(delta) < 10:  # Explicit minimum notional; avoids dust churn.
            return {"side": "hold", "quantity": 0, "price": price, "fee": 0}
        side = "buy" if delta > 0 else "sell"
        fill = price * (1 + SLIPPAGE if side == "buy" else 1 - SLIPPAGE)
        # Solve post-cost target allocation at reference price.
        if side == "buy":
            quantity = delta / (price + weight * (fill * (1 + FEE) - price))
            quantity = min(quantity, self.cash / (fill * (1 + FEE)))
        else:
            quantity = -delta / (price + weight * (fill * (1 - FEE) - price))
            quantity = min(quantity, self.btc)
        notional = quantity * fill
        fee = notional * FEE
        if side == "buy":
            self.cash -= notional + fee
            self.btc += quantity
        else:
            self.cash += notional - fee
            self.btc -= quantity
        self.cash = max(0.0, self.cash)
        self.btc = max(0.0, self.btc)
        self.fees += fee
        self.trades += 1
        return {"side": side, "quantity": quantity, "price": fill, "fee": fee}


def rule_decision(candles):
    """Transparent 12/48-bar moving-average trend baseline."""
    closes = [c["close"] for c in candles[-48:]]
    fast = sum(closes[-12:]) / len(closes[-12:])
    slow = sum(closes) / len(closes)
    target = 100 if fast > slow * 1.002 else 0 if fast < slow * 0.998 else 50
    return {"target": target, "probabilities": {}, "latency_ms": 0,
            "source": "rule", "note": "12/48봉 이동평균 · ±0.2% 중립 구간"}

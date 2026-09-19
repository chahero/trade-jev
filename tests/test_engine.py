import pytest
from server.engine import Account, FEE, SLIPPAGE


def test_full_allocation_includes_fee_without_negative_cash():
    account = Account()
    fill = account.rebalance(100, 100_000)
    assert fill["price"] == pytest.approx(100_000 * (1 + SLIPPAGE))
    assert account.btc == pytest.approx(10_000 / (fill["price"] * (1 + FEE)))
    assert account.cash == pytest.approx(0, abs=1e-9)
    assert account.fees == pytest.approx(fill["quantity"] * fill["price"] * FEE)
    account.rebalance(0, 100_000)
    assert account.btc == 0
    assert 9960 < account.cash < 10000


def test_target_post_cost_weight_and_hold_dust():
    account = Account()
    account.rebalance(50, 80_000)
    assert account.btc * 80_000 / account.value(80_000) == pytest.approx(.5)
    fees = account.fees
    assert account.rebalance(50, 80_000)["side"] == "hold"
    assert account.fees == fees
    account.rebalance(25, 120_000)
    assert account.btc * 120_000 / account.value(120_000) == pytest.approx(.25)


def test_drawdown_stays_at_historical_maximum():
    account = Account(cash=0, btc=1, peak=100)
    assert account.snapshot(80)["max_drawdown"] == pytest.approx(.2)
    assert account.snapshot(120)["max_drawdown"] == pytest.approx(.2)
    assert account.snapshot(60)["max_drawdown"] == pytest.approx(.5)


@pytest.mark.parametrize("price", [0, -1, float('inf'), float('nan')])
def test_invalid_price_rejected(price):
    with pytest.raises(ValueError):
        Account().rebalance(100, price)

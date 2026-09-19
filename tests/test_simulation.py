from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from server import app as service, market
from server.engine import SLIPPAGE


@pytest.fixture
def run(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "DB", tmp_path / "runs.sqlite3")
    candles = [{"time": n * market.BAR_MS, "open": 100+n, "high": 102+n,
                "low": 99+n, "close": 101+n, "volume": 1000} for n in range(100)]
    result = service.initial_run(service.NewRun(strategy="jev"), candles, 96)
    service.save(result)
    return result


def test_no_future_candles_and_next_open_execution(run, monkeypatch):
    seen = []
    def choose(candles, account):
        seen.extend(deepcopy(candles))
        return {"target": 100, "probabilities": {}, "source": "jev", "latency_ms": 1, "note": "test"}
    monkeypatch.setattr(service.policy, "choose", choose)
    assert len(service.public(run)["candles"]) == 96
    service.historical_step(run)
    assert len(seen) == 96
    assert seen[-1]["time"] < run["events"][0]["time"]
    assert run["events"][0]["price"] == pytest.approx(196*(1+SLIPPAGE))
    assert run["account"]["equity"] == pytest.approx(run["account"]["cash"] + run["account"]["btc"]*197)
    assert len(service.public(run)["candles"]) == 97
    assert service.read(run["id"])["events"] == run["events"]


def test_call_cap_and_failures_are_persisted(run, monkeypatch):
    run["max_calls"] = 1
    def fail(*args):
        raise RuntimeError("provider failure")
    monkeypatch.setattr(service.policy, "choose", fail)
    with pytest.raises(RuntimeError):
        service.historical_step(run)
    assert service.read(run["id"])["calls"] == 1
    assert run["cursor"] == 96
    with pytest.raises(ValueError, match="호출 한도"):
        service.historical_step(run)
    assert not run["events"]


def test_rule_baseline_matches_selected_rule(run):
    run["strategy"] = "rule"
    for _ in range(4):
        service.historical_step(run)
    assert run["finished"]
    assert run["calls"] == 0
    assert all(p["equity"] == p["rule"] for p in run["points"])
    before = deepcopy(run)
    service.historical_step(run)
    assert run == before


def test_live_quote_requested_after_inference_once_per_bar(run, monkeypatch):
    run["mode"] = "live"
    calls = []
    bars = run["bars"][:96]
    monkeypatch.setattr(market, "recent", lambda: bars)
    def choose(*args):
        calls.append("inference")
        return {"target": 100, "probabilities": {}, "source": "jev", "latency_ms": 1, "note": "test"}
    def ticker():
        calls.append("quote")
        return 500
    monkeypatch.setattr(service.policy, "choose", choose)
    monkeypatch.setattr(market, "ticker", ticker)
    service.live_tick(run)
    service.live_tick(run)
    assert calls == ["inference", "quote", "quote"]
    assert run["calls"] == 1
    assert len(run["events"]) == 1
    assert run["events"][0]["price"] == pytest.approx(500 * (1 + SLIPPAGE))


def test_market_rejects_gap_and_duplicate():
    with pytest.raises(ValueError):
        market.validate([{"time": 0}, {"time": 2*market.BAR_MS}])
    with pytest.raises(ValueError):
        market.validate([{"time": 0}, {"time": 0}])


def test_api_rejects_cross_origin_and_invalid_dates(run):
    with TestClient(service.app) as client:
        assert client.post('/api/runs', json={}, headers={"origin": "https://evil.example"}).status_code == 403
        assert client.post('/api/runs', json={"start": "2025-01-08", "end": "2025-01-01"}).status_code == 400
        payload=client.get(f'/api/runs/{run["id"]}').json()
        assert "bars" not in payload and "accounts" not in payload
        assert len(payload["candles"]) == 96


def test_restart_pauses_live_accounts(run):
    run["mode"] = "live"
    run["running"] = True
    service.save(run)
    with TestClient(service.app):
        assert not service.read(run["id"])["running"]


def test_export_is_downloadable_and_contains_only_observed_data(run):
    with TestClient(service.app) as client:
        response = client.get(f'/api/runs/{run["id"]}/export')
        assert response.status_code == 200
        assert response.headers['content-disposition'].startswith('attachment; filename="jev-')
        assert len(response.json()['candles']) == 96
        assert 'TYPESAFE_API_KEY' not in response.text
        assert 'bars' not in response.json()

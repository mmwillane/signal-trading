"""Tests du journal de trades : ajout, clôture, calcul d'espérance,
validation des entrées. Utilise un fichier de stockage temporaire.
"""

from __future__ import annotations

import pytest

from src.journal import store


@pytest.fixture(autouse=True)
def _temp_store(tmp_path, monkeypatch):
    """Redirige le stockage vers un fichier temporaire par test."""
    monkeypatch.setattr(store, "_STORE_PATH", tmp_path / "journal.json")
    yield


def _sample(**kw):
    base = {
        "symbol": "AAPL", "direction": "buy", "entry": 100.0,
        "stop": 95.0, "take_profit": 110.0, "quantity": 10, "confidence": 70,
    }
    base.update(kw)
    return base


def test_add_and_list():
    t = store.add_trade(_sample())
    assert t.status == "open"
    assert t.risk_amount == 50.0            # 10 * |100-95|
    rows = store.list_trades()
    assert len(rows) == 1 and rows[0]["symbol"] == "AAPL"


def test_add_rejects_bad_input():
    with pytest.raises(store.JournalError):
        store.add_trade(_sample(direction="hold"))
    with pytest.raises(store.JournalError):
        store.add_trade(_sample(entry=100.0, stop=100.0))  # entry == stop
    with pytest.raises(store.JournalError):
        store.add_trade(_sample(quantity=0))


def test_close_computes_r_multiple_win():
    t = store.add_trade(_sample())          # risque/unité = 5
    closed = store.close_trade(t.id, exit_price=110.0)  # +10 => +2R
    assert closed.status == "closed"
    assert closed.r_multiple == 2.0


def test_close_computes_r_multiple_loss():
    t = store.add_trade(_sample())
    closed = store.close_trade(t.id, exit_price=95.0)   # -5 => -1R
    assert closed.r_multiple == -1.0


def test_short_direction_r_multiple():
    t = store.add_trade(_sample(direction="sell", entry=100.0, stop=105.0))
    closed = store.close_trade(t.id, exit_price=90.0)   # short gagne => +2R
    assert closed.r_multiple == 2.0


def test_cannot_close_twice():
    t = store.add_trade(_sample())
    store.close_trade(t.id, 110.0)
    with pytest.raises(store.JournalError):
        store.close_trade(t.id, 108.0)


def test_expectancy_math():
    a = store.add_trade(_sample())
    b = store.add_trade(_sample())
    c = store.add_trade(_sample())
    store.close_trade(a.id, 110.0)          # +2R
    store.close_trade(b.id, 110.0)          # +2R
    store.close_trade(c.id, 95.0)           # -1R
    exp = store.expectancy()
    assert exp.n_closed == 3
    assert abs(exp.win_rate - 2 / 3) < 1e-3     # arrondi à 4 décimales
    assert exp.total_r == 3.0               # 2 + 2 - 1
    assert abs(exp.expectancy_r - 1.0) < 1e-3   # (2+2-1)/3
    assert exp.profit_factor == 4.0         # 4 / 1


def test_delete_trade():
    t = store.add_trade(_sample())
    assert store.delete_trade(t.id) is True
    assert store.list_trades() == []
    assert store.delete_trade("nope") is False

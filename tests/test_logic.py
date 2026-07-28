"""Tests unitaires de la logique (sans réseau) : indicateurs, décision,
sizing, proposition, backtest. Données synthétiques déterministes.

Principe de test : la logique de DÉCISION (evaluate_row) est testée avec
des valeurs d'indicateurs explicites — déterministe et indépendant de la
dynamique des indicateurs. Les intégrations (backtest) utilisent une série
calibrée pour déclencher réellement des trades.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis import indicators as ind
from src.analysis.analyzer import Signal, compute_features, evaluate_row
from src.backtest.engine import run_backtest
from src.proposal.order_proposal import build_proposal
from src.proposal.position_sizing import size_position


def _uptrend_df(n: int = 300) -> pd.DataFrame:
    """Série haussière bruitée, OHLCV cohérent (pour tester les indicateurs)."""
    rng = np.random.default_rng(42)
    close = np.linspace(100, 200, n) + rng.normal(0, 1.0, n)
    high = close + np.abs(rng.normal(0.5, 0.3, n))
    low = close - np.abs(rng.normal(0.5, 0.3, n))
    open_ = close - rng.normal(0, 0.4, n)
    vol = rng.integers(1_000, 5_000, n).astype(float)
    idx = pd.date_range("2022-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol},
        index=idx,
    )


def _triggering_df(n: int = 420) -> pd.DataFrame:
    """Uptrend + oscillations calibrées pour produire des setups (pullback
    puis reprise) : le backtest y déclenche plusieurs trades."""
    rng = np.random.default_rng(5)
    t = np.arange(n)
    close = 100 + 0.25 * t + 8 * np.sin(t / 28.0) + rng.normal(0, 0.5, n)
    high = close + np.abs(rng.normal(0.4, 0.2, n))
    low = close - np.abs(rng.normal(0.4, 0.2, n))
    open_ = close - rng.normal(0, 0.3, n)
    vol = rng.integers(1_000, 5_000, n).astype(float)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol}
    )


# --- Indicateurs ---------------------------------------------------------
def test_rsi_bounds():
    rsi = ind.rsi(_uptrend_df()["Close"])
    assert rsi.min() >= 0 and rsi.max() <= 100


def test_atr_positive():
    atr = ind.atr(_uptrend_df()).dropna()
    assert (atr > 0).all()


def test_adx_robust_on_degenerate_data():
    """Un prix plat (True Range nul, DI dégénérés) ne doit pas planter l'ADX
    (régression : 'No numeric types to aggregate' observé sur certains titres)."""
    n = 60
    idx = pd.date_range("2022-01-01", periods=n, freq="D")
    flat = pd.DataFrame(
        {"Open": 100.0, "High": 100.0, "Low": 100.0, "Close": 100.0, "Volume": 1000.0},
        index=idx,
    )
    out = ind.adx(flat, 14)
    assert list(out.columns) == ["adx", "plus_di", "minus_di"]
    assert out["adx"].notna().all()
    # compute_features doit aussi survivre à ce cas.
    feat = compute_features(flat)
    assert "adx" in feat.columns and feat["adx"].notna().all()


def test_features_have_all_indicators():
    feat = compute_features(_uptrend_df())
    for col in ("sma_fast", "sma_slow", "sma_trend", "rsi", "macd_hist", "atr"):
        assert col in feat.columns


# --- Logique de décision (valeurs d'indicateurs explicites) --------------
def _row(**kw) -> pd.Series:
    base = {
        "Close": 150.0, "atr": 2.0, "sma_trend": 120.0,
        "sma_fast": 145.0, "sma_slow": 140.0, "macd_hist": 0.5, "rsi": 60.0,
        "adx": 30.0, "swing_low": 146.0, "swing_high": 154.0,
    }
    base.update(kw)
    return pd.Series(base)


def test_decision_buy_on_bullish_confluence():
    sig = evaluate_row(_row())
    assert sig.direction == "buy"
    assert sig.confidence >= 55


def test_decision_sell_on_bearish_confluence():
    row = _row(Close=100.0, sma_trend=130.0, sma_fast=105.0,
               sma_slow=110.0, macd_hist=-0.5, rsi=40.0,
               swing_low=96.0, swing_high=104.0)
    assert evaluate_row(row).direction == "sell"


def test_adx_gate_blocks_rangebound_market():
    # Toutes conditions haussières mais marché sans tendance (ADX faible).
    assert evaluate_row(_row(adx=12.0)).direction is None


def test_decision_none_when_overbought():
    # Toutes conditions haussières sauf RSI en surachat -> pas de setup.
    assert evaluate_row(_row(rsi=75.0)).direction is None


def test_decision_none_without_trend_alignment():
    # Prix sous la SMA200 : pas d'achat même si le momentum court est positif.
    assert evaluate_row(_row(sma_trend=160.0)).direction is None


def test_sentiment_veto_blocks_buy():
    # Un sentiment très négatif oppose son veto à un setup haussier.
    assert evaluate_row(_row(), sentiment_score=-0.5).direction is None


def test_multitimeframe_boosts_confidence():
    base = evaluate_row(_row(), mtf_trend=0).confidence
    aligned = evaluate_row(_row(), mtf_trend=1).confidence
    assert aligned > base  # l'alignement intraday renforce le score


def test_confidence_floor_rejects_weak_setup():
    # ADX juste au seuil + RSI hors zone idéale -> score sous le plancher.
    sig = evaluate_row(_row(adx=20.0, rsi=68.0, macd_hist=0.01), mtf_trend=-1)
    assert sig.direction is None


# --- Position sizing -----------------------------------------------------
def test_position_sizing_risk_fixed():
    size = size_position(capital=10_000, risk_per_trade=0.01, entry=100.0, stop=95.0)
    assert size is not None
    assert abs(size.risk_amount - 100.0) < 1e-6   # 1% de 10000
    assert abs(size.quantity - 20.0) < 1e-6       # 100 / 5


def test_position_sizing_no_leverage():
    size = size_position(capital=1_000, risk_per_trade=0.01, entry=100.0, stop=99.99)
    assert size is not None
    assert size.notional <= 1_000 + 1e-6


# --- Proposition ---------------------------------------------------------
def test_proposal_respects_min_rr():
    signal = Signal(
        direction="buy", reasons=("test",), atr=2.0, close=150.0,
        adx=30.0, confidence=70, swing_low=146.0, swing_high=154.0,
    )
    proposal = build_proposal("TEST", signal, capital=10_000, risk_per_trade=0.01)
    assert proposal is not None
    assert proposal.risk_reward >= 1.7
    assert proposal.stop_loss < proposal.entry < proposal.take_profit
    # Stop structurel : juste sous le plus bas récent (146).
    assert proposal.stop_loss < 146.0


def test_no_proposal_without_setup():
    signal = Signal(direction=None, reasons=("rien",), atr=2.0, close=150.0)
    assert build_proposal("X", signal, capital=10_000, risk_per_trade=0.01) is None


# --- Backtest (intégration) ---------------------------------------------
def test_backtest_triggers_and_is_consistent():
    stats, trades = run_backtest(_triggering_df())
    assert stats.n_trades > 0                      # la donnée déclenche bien
    assert 0.0 <= stats.win_rate <= 1.0
    # total_r cohérent avec la somme des R par trade
    assert abs(stats.total_r - round(sum(t.r_multiple for t in trades), 2)) < 0.05

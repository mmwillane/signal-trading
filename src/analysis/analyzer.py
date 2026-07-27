"""Détection de setup : confluence technique + force de tendance + score.

Améliorations math par rapport à la v1 :
- Filtre ADX : on ignore les marchés sans tendance (source n°1 de faux signaux).
- Score de confiance 0-100 : agrège toutes les confirmations pour classer les
  setups et n'en retenir que les plus solides.
- Confirmation multi-temporel (optionnelle) : un biais intraday aligné renforce
  le score, un biais opposé le pénalise.
- Niveaux structurels (swing) transportés pour un stop non arbitraire.

La logique reste réutilisée telle quelle par le backtest. Rien ici ne
« prédit » : on qualifie une confluence de conditions.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..knowledge import trading_rules as tr
from . import indicators as ind


@dataclass(frozen=True)
class Signal:
    direction: str | None          # "buy" | "sell" | None
    reasons: tuple[str, ...]
    atr: float
    close: float
    adx: float = 0.0
    confidence: int = 0            # 0-100
    swing_low: float = 0.0
    swing_high: float = 0.0
    mtf: str | None = None         # "aligné" | "opposé" | "neutre" | None

    @property
    def has_setup(self) -> bool:
        return self.direction is not None


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute tous les indicateurs au DataFrame OHLCV."""
    feat = df.copy()
    feat["sma_fast"] = ind.sma(df["Close"], 20)
    feat["sma_slow"] = ind.sma(df["Close"], 50)
    feat["sma_trend"] = ind.sma(df["Close"], tr.TREND_FILTER_WINDOW)
    feat["rsi"] = ind.rsi(df["Close"], 14)
    macd = ind.macd(df["Close"])
    feat["macd_hist"] = macd["hist"]
    feat["atr"] = ind.atr(df, 14)
    adx_df = ind.adx(df, 14)
    feat["adx"] = adx_df["adx"]
    feat["swing_low"] = ind.swing_low(df, tr.SWING_WINDOW)
    feat["swing_high"] = ind.swing_high(df, tr.SWING_WINDOW)
    return feat


def trend_direction(df: pd.DataFrame) -> int:
    """Biais de tendance simple pour une autre unité de temps (multi-temporel).

    +1 haussier, -1 baissier, 0 indéterminé. Basé sur EMA rapide vs lente +
    position du prix : robuste et peu coûteux sur de l'intraday.
    """
    if df is None or len(df) < 55:
        return 0
    close = df["Close"]
    ema_fast = float(ind.ema(close, 20).iloc[-1])
    ema_slow = float(ind.ema(close, 50).iloc[-1])
    last = float(close.iloc[-1])
    if last > ema_fast > ema_slow:
        return 1
    if last < ema_fast < ema_slow:
        return -1
    return 0


def evaluate_row(row: pd.Series, sentiment_score: float = 0.0, mtf_trend: int = 0) -> Signal:
    """Évalue une ligne de features enrichies en un Signal noté.

    Portes dures (toutes requises) : données valides, ADX >= seuil, alignement
    de tendance (SMA200), momentum court (SMA20/50), MACD, RSI non extrême.
    Puis score de confiance >= seuil, veto de sentiment, biais multi-temporel.
    """
    close = _f(row.get("Close"))
    atr = _f(row.get("atr"))
    if close is None or atr is None or atr <= 0:
        return Signal(None, ("données insuffisantes",), atr or 0.0, close or 0.0)

    trend = _f(row.get("sma_trend"))
    fast, slow = _f(row.get("sma_fast")), _f(row.get("sma_slow"))
    macd_hist = _f(row.get("macd_hist"))
    rsi = _f(row.get("rsi"))
    adx = _f(row.get("adx")) or 0.0
    swing_lo = _f(row.get("swing_low")) or 0.0
    swing_hi = _f(row.get("swing_high")) or 0.0
    if None in (trend, fast, slow, macd_hist, rsi):
        return Signal(None, ("indicateurs pas encore disponibles",), atr, close, adx)

    # --- Porte de force de tendance (ADX) : commune aux deux sens ---
    if adx < tr.ADX_MIN:
        return Signal(
            None, (f"marché sans tendance (ADX={adx:.0f} < {tr.ADX_MIN:.0f})",),
            atr, close, adx,
        )

    up = close > trend and fast > slow and macd_hist > 0 and rsi < 70
    down = close < trend and fast < slow and macd_hist < 0 and rsi > 30

    sentiment_blocks_up = sentiment_score <= -0.35
    sentiment_blocks_down = sentiment_score >= 0.35

    if up and not sentiment_blocks_up:
        return _score_and_build(
            "buy", close, atr, adx, rsi, macd_hist, sentiment_score, mtf_trend,
            swing_lo, swing_hi,
        )
    if down and not sentiment_blocks_down:
        return _score_and_build(
            "sell", close, atr, adx, rsi, macd_hist, sentiment_score, mtf_trend,
            swing_lo, swing_hi,
        )

    return Signal(None, ("pas de confluence suffisante",), atr, close, adx)


def _score_and_build(
    direction: str, close: float, atr: float, adx: float, rsi: float,
    macd_hist: float, sentiment: float, mtf_trend: int,
    swing_lo: float, swing_hi: float,
) -> Signal:
    """Calcule le score de confiance ; n'émet le signal que s'il dépasse le seuil."""
    buy = direction == "buy"
    reasons: list[str] = []
    score = 0

    # 1) Alignement de tendance (porte déjà franchie) — 15 pts.
    score += 15
    reasons.append(
        "prix > SMA200 (tendance haussière)" if buy else "prix < SMA200 (tendance baissière)"
    )

    # 2) Force de tendance ADX — 25 pts (linéaire de 15 à 40).
    adx_pts = round(_clamp((adx - 15) / (40 - 15), 0, 1) * 25)
    score += adx_pts
    reasons.append(f"tendance {'forte' if adx >= 30 else 'établie'} (ADX={adx:.0f})")

    # 3) MACD dans le sens — 12 pts.
    score += 12
    reasons.append(f"MACD {'haussier' if buy else 'baissier'} (hist={macd_hist:.3f})")

    # 4) Momentum court (SMA20/50) — 8 pts.
    score += 8
    reasons.append("SMA20 > SMA50 (momentum court)" if buy else "SMA20 < SMA50 (momentum court)")

    # 5) Zone RSI saine (marge pour courir sans surachat/survente) — 12 pts.
    if (buy and 40 <= rsi <= 65) or (not buy and 35 <= rsi <= 60):
        score += 12
        reasons.append(f"RSI={rsi:.0f} (zone idéale, marge de progression)")
    elif (buy and rsi < 70) or (not buy and rsi > 30):
        score += 6
        reasons.append(f"RSI={rsi:.0f} (acceptable)")

    # 6) Sentiment news dans le sens — 13 pts.
    aligned_sent = sentiment if buy else -sentiment
    sent_pts = round(_clamp(aligned_sent / 0.5, 0, 1) * 13)
    score += sent_pts
    if aligned_sent >= 0.15:
        reasons.append(f"sentiment news favorable ({sentiment:+.2f})")

    # 7) Confirmation multi-temporel — 15 pts.
    mtf_label = "neutre"
    aligned_mtf = (buy and mtf_trend == 1) or (not buy and mtf_trend == -1)
    if aligned_mtf:
        score += 15
        mtf_label = "aligné"
        reasons.append("intraday aligné avec le journalier")
    elif mtf_trend == 0:
        score += 7  # inconnu : demi-crédit
    else:
        mtf_label = "opposé"
        reasons.append("intraday à contre-courant (prudence)")

    score = int(_clamp(score, 0, 100))

    if score < tr.CONFIDENCE_MIN:
        return Signal(
            None, (f"setup trop faible (confiance {score}/100 < {tr.CONFIDENCE_MIN})",),
            atr, close, adx, score, swing_lo, swing_hi, mtf_label,
        )

    return Signal(direction, tuple(reasons), atr, close, adx, score, swing_lo, swing_hi, mtf_label)


def evaluate_latest(df: pd.DataFrame, sentiment_score: float = 0.0, mtf_trend: int = 0) -> Signal:
    """Évalue la dernière bougie disponible."""
    feat = compute_features(df)
    return evaluate_row(feat.iloc[-1], sentiment_score, mtf_trend)


def _f(value: object) -> float | None:
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # exclut NaN


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

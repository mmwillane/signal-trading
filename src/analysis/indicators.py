"""Indicateurs techniques classiques, implémentés à la main sur pandas.

Choix expliqué :
- Pas de dépendance TA-Lib (compilation native pénible sous Windows).
  numpy/pandas suffisent et rendent chaque formule lisible et auditable.
- Toutes les fonctions renvoient des Series alignées sur l'index du prix,
  pour être combinées sans réindexation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(close: pd.Series, window: int) -> pd.Series:
    """Moyenne mobile simple."""
    return close.rolling(window=window, min_periods=window).mean()


def ema(close: pd.Series, window: int) -> pd.Series:
    """Moyenne mobile exponentielle."""
    return close.ewm(span=window, adjust=False).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """RSI de Wilder. Renvoie une valeur dans [0, 100]."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    # Lissage de Wilder = EMA avec alpha = 1/window.
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
    # np.nan (et non pd.NA) : conserve le dtype float, ewm/arithmétique OK.
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100.0)


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """MACD : ligne MACD, ligne de signal, histogramme."""
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame(
        {
            "macd": macd_line,
            "signal": signal_line,
            "hist": macd_line - signal_line,
        }
    )


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """Average True Range (volatilité), lissage de Wilder.

    Sert au calcul du stop loss et de la taille de position.
    """
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / window, adjust=False).mean()


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, prev_close = df["High"], df["Low"], df["Close"].shift(1)
    return pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)


def adx(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """Average Directional Index (force de tendance) + composantes +DI/-DI.

    ADX ne dit PAS le sens, seulement la FORCE de la tendance :
      - ADX < 20  : marché sans tendance (range) -> signaux peu fiables.
      - ADX 20-40 : tendance établie.
      - ADX > 40  : tendance très forte.
    On l'utilise comme filtre : pas de setup si le marché n'a pas de tendance.
    """
    high, low = df["High"], df["Low"]
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move.clip(lower=0)
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move.clip(lower=0)

    # Robustesse : on remplace les 0 par np.nan (dtype float conservé, contrairement
    # à pd.NA qui bascule en object et casse ewm), et on force float64.
    atr_ = _true_range(df).ewm(alpha=1 / window, adjust=False).mean()
    atr_safe = atr_.replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1 / window, adjust=False).mean() / atr_safe
    minus_di = 100 * minus_dm.ewm(alpha=1 / window, adjust=False).mean() / atr_safe

    di_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = (100 * (plus_di - minus_di).abs() / di_sum)
    # Certaines séries (données dégénérées d'un symbole) donnent un dx tout-NaN :
    # on garantit un float64 sans NaN avant l'EWM pour ne jamais planter.
    dx = pd.to_numeric(dx, errors="coerce").astype("float64").fillna(0.0)
    adx_line = dx.ewm(alpha=1 / window, adjust=False).mean()

    return pd.DataFrame(
        {
            "adx": adx_line.fillna(0.0).astype("float64"),
            "plus_di": pd.to_numeric(plus_di, errors="coerce").fillna(0.0),
            "minus_di": pd.to_numeric(minus_di, errors="coerce").fillna(0.0),
        }
    )


def swing_low(df: pd.DataFrame, window: int = 10) -> pd.Series:
    """Plus bas récent sur `window` bougies (support structurel pour un stop long)."""
    return df["Low"].rolling(window=window, min_periods=1).min()


def swing_high(df: pd.DataFrame, window: int = 10) -> pd.Series:
    """Plus haut récent sur `window` bougies (résistance structurelle pour un stop short)."""
    return df["High"].rolling(window=window, min_periods=1).max()

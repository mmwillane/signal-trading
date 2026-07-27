"""Récupération des données de marché.

Choix de la source — yfinance :
- Gratuit, sans clé API, couvre actions / ETF / crypto (BTC-USD) et
  forex (EURUSD=X) : parfait pour un mode démo en lecture seule.
- Limites : données Yahoo non contractuelles, léger différé, pas de
  garantie de disponibilité. Acceptable pour de l'aide à la décision,
  PAS pour de l'exécution automatique (ce que l'outil ne fait jamais).
- L'interface ci-dessous isole yfinance : pour changer de fournisseur
  (Alpha Vantage, Polygon...), il suffit de réimplémenter get_history().
"""

from __future__ import annotations

import pandas as pd

from ..security.safe_logging import get_logger
from ..security.sanitize import clean_symbol

log = get_logger("data")

# Colonnes attendues après normalisation.
_OHLCV = ["Open", "High", "Low", "Close", "Volume"]


def get_history(
    symbol: str,
    *,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame | None:
    """Renvoie l'historique OHLCV nettoyé, ou None si indisponible.

    On valide le symbole, on capture toute erreur réseau/parse de
    yfinance, et on assainit le DataFrame avant de le rendre.
    """
    try:
        import yfinance as yf
    except ImportError:
        log.error("yfinance non installé : pip install -r requirements.txt")
        return None

    try:
        sym = clean_symbol(symbol)
    except ValueError as exc:
        log.warning("Symbole ignoré : %s", exc)
        return None

    try:
        df = yf.download(
            sym,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception as exc:  # yfinance remonte des erreurs hétérogènes
        log.warning("Échec téléchargement %s : %s", sym, type(exc).__name__)
        return None

    return _normalize(df, sym)


def _normalize(df: pd.DataFrame | None, sym: str) -> pd.DataFrame | None:
    """Aplati les colonnes, garde l'OHLCV, retire les lignes corrompues."""
    if df is None or df.empty:
        log.info("Aucune donnée pour %s", sym)
        return None

    # yfinance renvoie parfois un MultiIndex de colonnes (Prix, Ticker).
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    missing = [c for c in _OHLCV if c not in df.columns]
    if missing:
        log.warning("Colonnes manquantes pour %s : %s", sym, missing)
        return None

    df = df[_OHLCV].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=["Close"])  # une clôture NaN casse tous les indicateurs
    if df.empty:
        return None
    df.attrs["symbol"] = sym
    return df


def latest_price(df: pd.DataFrame) -> float:
    """Dernière clôture disponible."""
    return float(df["Close"].iloc[-1])


def get_intraday(symbol: str, *, interval: str = "60m", period: str = "1mo") -> pd.DataFrame | None:
    """Historique intraday (multi-temporel / graphique live).

    Rappel honnête : sur données gratuites, l'intraday actions est différé
    (~15 min). Pour la crypto, il est quasi temps réel.
    """
    return get_history(symbol, period=period, interval=interval)


def get_quote_price(symbol: str) -> float | None:
    """Dernier prix le plus frais possible (bougies 1 min du jour).

    Utilisé par l'endpoint de cotation live. Renvoie None si indisponible
    (marché fermé sans données intraday, etc.) — l'appelant se rabat alors
    sur la dernière clôture connue.
    """
    df = get_history(symbol, period="1d", interval="1m")
    if df is None or df.empty:
        return None
    return float(df["Close"].iloc[-1])

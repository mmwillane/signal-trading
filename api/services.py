"""Pont entre la logique métier (src/) et l'API HTTP.

Chaque fonction renvoie des structures JSON-sérialisables. On met en
cache les appels réseau (yfinance, news) via api.cache pour garder l'UI
réactive sans marteler les sources.

RAPPEL : rien ici n'exécute d'ordre. On ne fait que lire et analyser.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.analysis.analyzer import (
    compute_features,
    evaluate_latest,
    evaluate_row,
    trend_direction,
)
from src.backtest.engine import run_backtest
from src.data.market_data import get_history, get_intraday, get_quote_price, latest_price
from src.knowledge import trading_rules as tr
from src.news.news_feed import fetch_news, filter_for_symbol
from src.news.sentiment import score_news
from src.proposal.order_proposal import build_proposal
from src.security.env import Settings, load_settings

from .cache import get_or_set

# TTL (secondes) : plus court pour le live, plus long pour news / multi-temporel.
_HISTORY_TTL = 300
_NEWS_TTL = 900
_INTRADAY_TTL = 600      # bougies intraday (multi-temporel / graphique)
_QUOTE_TTL = 20          # prix live : rafraîchi ~toutes les 20 s
_MTF_TTL = 600           # biais multi-temporel


# --------------------------------------------------------------------------
def settings() -> Settings:
    # Rechargé à chaque fois (léger) pour refléter un .env modifié à chaud.
    return load_settings()


def settings_dict() -> dict[str, Any]:
    s = settings()
    return {
        "capital": s.capital,
        "risk_per_trade": s.risk_per_trade,
        "risk_amount": s.risk_amount(),
        "base_currency": s.base_currency,
        "watchlist": list(s.watchlist),
        "asset_class": s.asset_class,
        "principles": [
            {"name": r.name, "principle": r.principle, "rationale": r.rationale}
            for r in tr.RULES
        ],
    }


# --------------------------------------------------------------------------
def _history_cached(symbol: str, period: str = "1y") -> pd.DataFrame | None:
    return get_or_set(
        f"hist:{symbol}:{period}",
        _HISTORY_TTL,
        lambda: get_history(symbol, period=period, interval="1d"),
    )


def _news_cached() -> list:
    return get_or_set("news:all", _NEWS_TTL, fetch_news)


def _intraday_cached(symbol: str, interval: str = "60m", period: str = "1mo") -> pd.DataFrame | None:
    return get_or_set(
        f"intra:{symbol}:{interval}:{period}",
        _INTRADAY_TTL,
        lambda: get_intraday(symbol, interval=interval, period=period),
    )


# --- Unités de temps d'ANALYSE (style de trading) --------------------------
# tf -> (intervalle yfinance, période, TTL cache secondes)
_TF_CONFIG: dict[str, tuple[str, str, int]] = {
    "1d": ("1d", "1y", 300),     # swing / position (journalier)
    "1h": ("60m", "6mo", 600),   # trading horaire
    "15m": ("15m", "1mo", 240),  # intraday
    "5m": ("5m", "1mo", 120),    # intraday rapide
    "1m": ("1m", "7d", 60),      # scalping (données ~7 j seulement)
}


def _resolve_tf(tf: str | None) -> str:
    return tf if tf in _TF_CONFIG else "1d"


def _tf_history(symbol: str, tf: str) -> pd.DataFrame | None:
    """Historique à l'unité de temps demandée (cache adapté à la fréquence)."""
    interval, period, ttl = _TF_CONFIG[tf]
    if tf == "1d":
        return _history_cached(symbol)
    return get_or_set(
        f"tfhist:{symbol}:{tf}",
        ttl,
        lambda: get_history(symbol, period=period, interval=interval),
    )


def _mtf_bias(symbol: str, tf: str = "1d") -> int:
    """Biais de tendance d'une unité de temps de CONTEXTE (+1/-1/0).

    - En journalier : on confirme avec le 60 min (plus fin) = timing d'entrée.
    - En intraday : on confirme avec le JOURNALIER (unité supérieure) = « trader
      dans le sens de la grande tendance », principe classique du multi-temporel.
    """
    def _compute() -> int:
        secondary = _intraday_cached(symbol) if tf == "1d" else _history_cached(symbol)
        return trend_direction(secondary)

    return get_or_set(f"mtf:{symbol}:{tf}", _MTF_TTL, _compute)


def _quote_cached(symbol: str) -> float | None:
    """Prix live (cache court). None si indisponible."""
    return get_or_set(f"quote:{symbol}", _QUOTE_TTL, lambda: get_quote_price(symbol))


def _live_price(symbol: str, daily: pd.DataFrame) -> tuple[float, float, bool]:
    """Renvoie (prix, variation %, is_live).

    Le prix live vient des bougies 1 min ; la variation est calculée contre
    la clôture de la veille (issue du daily en cache). Repli sur la dernière
    clôture connue si l'intraday est indisponible.
    """
    prev_close = float(daily["Close"].iloc[-2]) if len(daily) >= 2 else float(daily["Close"].iloc[-1])
    live = _quote_cached(symbol)
    if live is not None and prev_close:
        return round(live, 4), round((live - prev_close) / prev_close * 100, 2), True
    last = latest_price(daily)
    return round(last, 4), _change_pct(daily), False


def _change_pct(df: pd.DataFrame) -> float:
    if len(df) < 2:
        return 0.0
    prev = float(df["Close"].iloc[-2])
    last = float(df["Close"].iloc[-1])
    return round((last - prev) / prev * 100, 2) if prev else 0.0


def _spark(df: pd.DataFrame, n: int = 40) -> list[float]:
    return [round(float(x), 4) for x in df["Close"].tail(n).tolist()]


# --------------------------------------------------------------------------
# Devises supportées à l'affichage. Le capital est saisi dans cette devise ;
# on le convertit en USD pour dimensionner (les instruments sont cotés en USD).
_SUPPORTED_CURRENCIES = {
    "USD", "EUR", "GBP", "NGN", "GHS", "KES", "ZAR", "XOF", "XAF", "MAD",
}
_FX_TTL = 3600  # taux de change mis en cache 1 h


def _fx_rate(currency: str) -> float:
    """Taux « combien de devise locale pour 1 USD ». USD -> 1.0.

    Repli sur 1.0 (comme si USD) si le taux est indisponible, pour ne jamais
    planter le calcul.
    """
    currency = (currency or "USD").upper()
    if currency == "USD":
        return 1.0

    def _fetch() -> float:
        from src.data.market_data import get_history

        df = get_history(f"USD{currency}=X", period="5d", interval="1d", max_retries=2)
        if df is None or df.empty:
            return 1.0
        rate = float(df["Close"].iloc[-1])
        return rate if rate > 0 else 1.0

    return get_or_set(f"fx:{currency}", _FX_TTL, _fetch)


def _resolve_currency(currency: str | None) -> str:
    c = (currency or "USD").upper()
    return c if c in _SUPPORTED_CURRENCIES else "USD"


def _effective_risk(
    capital: float | None, risk: float | None, currency: str | None = None
) -> tuple[float, float, str, float]:
    """Résout (capital_en_USD, risque, devise, taux_fx).

    Le capital fourni est exprimé dans la devise de l'utilisateur : on le
    convertit en USD pour le dimensionnement. On ne fait JAMAIS confiance au
    client : capital > 0, risque dans ]0, 0.1].
    """
    s = settings()
    cur = _resolve_currency(currency)
    fx = _fx_rate(cur)  # devise locale par USD

    cap_local = capital if (capital is not None and capital > 0) else s.capital * fx
    rsk = risk if (risk is not None and 0 < risk <= 0.1) else s.risk_per_trade

    cap_usd = cap_local / fx if fx > 0 else cap_local
    cap_usd = min(max(cap_usd, 1.0), 1_000_000_000.0)
    return cap_usd, rsk, cur, fx


def analyze_symbol(
    symbol: str,
    *,
    use_news: bool = True,
    capital: float | None = None,
    risk: float | None = None,
    fractional: bool = False,
    more_signals: bool = False,
    currency: str | None = None,
    tf: str = "1d",
) -> dict[str, Any]:
    """Analyse un instrument pour la vue liste (dashboard).

    `tf` = unité de temps d'analyse (1m/5m/15m/1h/1d) = style de trading. Toute
    la logique de setup s'applique aux bougies de cette unité (stop/objectif via
    l'ATR de l'unité choisie -> naturellement plus serrés en intraday).

    Le prix reste dans la devise de l'instrument (USD) ; les montants de compte
    sont convertis dans la devise de l'utilisateur.
    """
    cap, rsk, cur, fx = _effective_risk(capital, risk, currency)
    tf = _resolve_tf(tf)
    df = _tf_history(symbol, tf)
    if df is None or len(df) < tr.TREND_FILTER_WINDOW:
        return {
            "symbol": symbol,
            "status": "insufficient_data",
            "message": "Données insuffisantes",
        }

    sentiment = 0.0
    if use_news:
        sentiment = score_news(filter_for_symbol(_news_cached(), symbol)).score

    mtf = _mtf_bias(symbol, tf)
    signal = evaluate_latest(df, sentiment, mtf, loose=more_signals)
    if tf == "1d":
        price, change_pct, is_live = _live_price(symbol, df)
    else:
        # En intraday, la dernière bougie est déjà fraîche.
        price, change_pct, is_live = round(latest_price(df), 4), _change_pct(df), True

    result: dict[str, Any] = {
        "symbol": symbol,
        "status": "ok",
        "price": price,
        "change_pct": change_pct,
        "is_live": is_live,
        "sentiment": round(sentiment, 2),
        "spark": _spark(df),
        "has_setup": signal.has_setup,
        "direction": signal.direction,
        "confidence": signal.confidence,
        "adx": round(signal.adx, 1),
        "mtf": signal.mtf,
        "reasons": list(signal.reasons),
    }

    if signal.has_setup:
        # Crypto (paires -USD) toujours fractionnable ; actions selon le choix
        # de l'utilisateur (son broker permet ou non les fractions).
        allow_frac = fractional or symbol.upper().endswith("-USD")
        proposal = build_proposal(
            symbol, signal,
            capital=cap,
            risk_per_trade=rsk,
            sentiment_score=sentiment,
            allow_fractional=allow_frac,
        )
        if proposal is not None:
            result["proposal"] = _proposal_dict(proposal, fx, cur)
        else:
            # En pratique, avec un setup valide, l'échec vient du budget :
            # 1 action entière dépasse le capital / le risque autorisé.
            result["has_setup"] = False
            result["setup_unaffordable"] = True
            result["reasons"] = [
                f"Budget trop faible pour 1 action entière de {symbol}. "
                "Active « actions fractionnées » (si ton broker les permet) "
                "ou vise un instrument moins cher / une crypto."
            ]

    return result


def _proposal_dict(p, fx: float = 1.0, currency: str = "USD") -> dict[str, Any]:
    # Forex (paires yfinance en =X) : le volume MT5 s'exprime en LOTS
    # (1 lot = 100 000 unités de la devise de base).
    is_forex = p.symbol.upper().endswith("=X")
    lots = round(p.size.quantity / 100_000, 2) if is_forex else None

    # DISTANCES (robustes à l'écart de prix entre l'app et le broker) : on
    # entre AU MARCHÉ et on applique ces distances depuis le prix réel du broker.
    stop_dist = abs(p.entry - p.stop_loss)
    tp_dist = abs(p.take_profit - p.entry)
    stop_pct = round(stop_dist / p.entry * 100, 2) if p.entry else 0.0
    tp_pct = round(tp_dist / p.entry * 100, 2) if p.entry else 0.0
    stop_pips = round(stop_dist / 0.0001) if is_forex else None
    tp_pips = round(tp_dist / 0.0001) if is_forex else None

    return {
        "symbol": p.symbol,
        "direction": p.direction,
        # Prix INDICATIFS (données différées) — dans la devise de l'instrument (USD).
        "entry": p.entry,
        "stop_loss": p.stop_loss,
        "take_profit": p.take_profit,
        # Distances à appliquer depuis le prix réel du broker (entrée au marché).
        "stop_pct": stop_pct,
        "tp_pct": tp_pct,
        "stop_pips": stop_pips,
        "tp_pips": tp_pips,
        "risk_reward": p.risk_reward,
        "quantity": p.size.quantity,
        "is_forex": is_forex,
        "lots": lots,          # volume MT5 (lots) pour le forex, sinon null
        # Montants de compte : convertis dans la devise de l'utilisateur.
        "notional": round(p.size.notional * fx, 2),
        "risk_amount": round(p.size.risk_amount * fx, 2),
        "currency": currency,
        "reasons": list(p.reasons),
        "sentiment": p.sentiment,
        "confidence": p.confidence,
        "adx": p.adx,
        "stop_basis": p.stop_basis,
        "trailing_rule": p.trailing_rule,
    }


def _safe_analyze(
    symbol: str, *, use_news: bool, capital: float | None, risk: float | None,
    fractional: bool, more_signals: bool, currency: str | None, tf: str,
) -> dict[str, Any]:
    """Analyse un symbole en isolant toute erreur : un symbole défaillant
    ne doit jamais faire échouer l'ensemble du dashboard."""
    try:
        return analyze_symbol(
            symbol, use_news=use_news, capital=capital, risk=risk,
            fractional=fractional, more_signals=more_signals, currency=currency, tf=tf,
        )
    except Exception as exc:  # noqa: BLE001 - robustesse volontaire
        from src.security.safe_logging import get_logger

        get_logger("api").warning("Analyse échouée pour %s : %s", symbol, type(exc).__name__)
        return {"symbol": symbol, "status": "error", "message": "Analyse indisponible"}


def dashboard(
    *,
    use_news: bool = True,
    capital: float | None = None,
    risk: float | None = None,
    fractional: bool = False,
    more_signals: bool = False,
    currency: str | None = None,
    tf: str = "1d",
) -> dict[str, Any]:
    """Analyse toute la watchlist, setups les plus confiants d'abord."""
    s = settings()
    tf = _resolve_tf(tf)
    # Conversion pour les montants affichés ; l'analyse reçoit le capital
    # d'ORIGINE (en devise utilisateur) et convertit elle-même une seule fois.
    cap_usd, rsk, cur, fx = _effective_risk(capital, risk, currency)
    # En intraday, les news (biais lent) sont peu pertinentes -> on les ignore.
    use_news_eff = use_news and tf == "1d"
    items = [
        _safe_analyze(
            sym, use_news=use_news_eff, capital=capital, risk=risk,
            fractional=fractional, more_signals=more_signals, currency=currency, tf=tf,
        )
        for sym in s.watchlist
    ]
    # Tri : setups d'abord, puis par score de confiance décroissant.
    items.sort(key=lambda i: (i.get("has_setup", False), i.get("confidence", 0)), reverse=True)
    setups = [i for i in items if i.get("has_setup")]
    return {
        "generated_for": cur,
        "currency": cur,
        "fx_rate": round(fx, 6),
        "timeframe": tf,
        "capital": round(cap_usd * fx, 2),          # dans la devise utilisateur
        "risk_per_trade": rsk,
        "risk_amount": round(cap_usd * rsk * fx, 2),  # dans la devise utilisateur
        "n_setups": len(setups),
        "items": items,
    }


def quotes(symbols: list[str]) -> dict[str, Any]:
    """Cotations live légères (prix + variation) pour un rafraîchissement rapide."""
    out = {}
    for sym in symbols:
        sym = sym.upper()
        daily = _history_cached(sym)
        if daily is None or daily.empty:
            continue
        price, change_pct, is_live = _live_price(sym, daily)
        out[sym] = {"price": price, "change_pct": change_pct, "is_live": is_live}
    return {"quotes": out}


# --------------------------------------------------------------------------
def instrument_detail(
    symbol: str,
    *,
    use_news: bool = True,
    tf: str = "1d",
    capital: float | None = None,
    risk: float | None = None,
    fractional: bool = False,
    more_signals: bool = False,
    currency: str | None = None,
) -> dict[str, Any]:
    """Détail complet d'un instrument à l'unité de temps `tf`.

    L'analyse (setup, proposition) ET le graphique utilisent la même unité de
    temps (1m/5m/15m/1h/1d) = le style de trading choisi.
    """
    tf = _resolve_tf(tf)
    df = _tf_history(symbol, tf)
    if df is None or len(df) < tr.TREND_FILTER_WINDOW:
        return {"symbol": symbol, "status": "insufficient_data"}

    feat = compute_features(df)
    intraday = tf != "1d"
    candles, sma20, sma50 = _chart_from_feat(feat, intraday)

    last = feat.iloc[-1]
    sentiment = 0.0
    news_items: list = []
    if use_news and tf == "1d":  # news = biais lent, pertinent surtout en daily
        news_items = filter_for_symbol(_news_cached(), symbol)
        sentiment = score_news(news_items).score

    mtf = _mtf_bias(symbol, tf)
    signal = evaluate_row(last, sentiment, mtf, loose=more_signals)
    base = analyze_symbol(
        symbol, use_news=(use_news and tf == "1d"), capital=capital, risk=risk,
        fractional=fractional, more_signals=more_signals, currency=currency, tf=tf,
    )
    if tf == "1d":
        price, change_pct, is_live = _live_price(symbol, df)
    else:
        price, change_pct, is_live = round(latest_price(df), 4), _change_pct(df), True

    return {
        "symbol": symbol,
        "status": "ok",
        "price": price,
        "change_pct": change_pct,
        "is_live": is_live,
        "timeframe": tf,
        "currency": _resolve_currency(currency),
        "candles": candles,
        "sma20": sma20,
        "sma50": sma50,
        "indicators": {
            "rsi": round(float(last["rsi"]), 1),
            "macd_hist": round(float(last["macd_hist"]), 4),
            "atr": round(float(last["atr"]), 4),
            "adx": round(float(last["adx"]), 1),
            "sma_trend": round(float(last["sma_trend"]), 4),
        },
        "sentiment": round(sentiment, 2),
        "confidence": signal.confidence,
        "adx": round(signal.adx, 1),
        "mtf": signal.mtf,
        "has_setup": base.get("has_setup", False),
        "direction": signal.direction,
        "reasons": list(signal.reasons),
        "proposal": base.get("proposal"),
        "news": [_news_dict(n) for n in news_items[:6]],
    }


def _chart_from_feat(feat: pd.DataFrame, intraday: bool):
    """Construit chandeliers + SMA20/50 depuis un DataFrame de features, quelle
    que soit l'unité de temps (format d'horodatage adapté)."""
    tail = feat.tail(200)
    fmt = (lambda ts: ts.isoformat()) if intraday else (lambda ts: ts.strftime("%Y-%m-%d"))
    candles = [
        {
            "time": fmt(ts),
            "open": round(float(r.Open), 4),
            "high": round(float(r.High), 4),
            "low": round(float(r.Low), 4),
            "close": round(float(r.Close), 4),
        }
        for ts, r in tail.iterrows()
    ]
    sma20 = [{"time": fmt(ts), "value": round(float(v), 4)} for ts, v in tail["sma_fast"].dropna().items()]
    sma50 = [{"time": fmt(ts), "value": round(float(v), 4)} for ts, v in tail["sma_slow"].dropna().items()]
    return candles, sma20, sma50


def _chart_daily(feat: pd.DataFrame):
    tail = feat.tail(180)  # ~6 mois
    candles = [
        {
            "time": ts.strftime("%Y-%m-%d"),
            "open": round(float(r.Open), 4),
            "high": round(float(r.High), 4),
            "low": round(float(r.Low), 4),
            "close": round(float(r.Close), 4),
        }
        for ts, r in tail.iterrows()
    ]
    sma20 = [{"time": ts.strftime("%Y-%m-%d"), "value": round(float(v), 4)} for ts, v in tail["sma_fast"].dropna().items()]
    sma50 = [{"time": ts.strftime("%Y-%m-%d"), "value": round(float(v), 4)} for ts, v in tail["sma_slow"].dropna().items()]
    return candles, sma20, sma50


def _chart_intraday(intra: pd.DataFrame | None):
    if intra is None or intra.empty:
        return [], [], []
    from src.analysis import indicators as ind

    tail = intra.tail(180)
    ema20 = ind.ema(tail["Close"], 20)
    ema50 = ind.ema(tail["Close"], 50)
    candles = [
        {
            "time": ts.isoformat(),
            "open": round(float(r.Open), 4),
            "high": round(float(r.High), 4),
            "low": round(float(r.Low), 4),
            "close": round(float(r.Close), 4),
        }
        for ts, r in tail.iterrows()
    ]
    sma20 = [{"time": ts.isoformat(), "value": round(float(v), 4)} for ts, v in ema20.items()]
    sma50 = [{"time": ts.isoformat(), "value": round(float(v), 4)} for ts, v in ema50.items()]
    return candles, sma20, sma50


# --------------------------------------------------------------------------
def _news_dict(n) -> dict[str, Any]:
    return {
        "source": n.source,
        "title": n.title,
        "summary": n.summary[:280],
        "url": n.url,
        "themes": list(n.macro_themes),
    }


def news_feed() -> dict[str, Any]:
    items = _news_cached()
    overall = score_news(items)
    return {
        "overall_sentiment": overall.score,
        "label": overall.label,
        "count": len(items),
        "items": [_news_dict(n) for n in items[:40]],
    }


# --------------------------------------------------------------------------
def backtest(symbol: str, period: str = "2y", trailing: bool = True) -> dict[str, Any]:
    df = _history_cached(symbol, period=period)
    if df is None or len(df) < tr.TREND_FILTER_WINDOW + 10:
        return {"symbol": symbol, "status": "insufficient_data"}

    stats, trades = run_backtest(df, use_trailing=trailing)
    pf = stats.profit_factor
    return {
        "symbol": symbol,
        "status": "ok",
        "period": period,
        "trailing": trailing,
        "stats": {
            "n_trades": stats.n_trades,
            "win_rate": round(stats.win_rate, 4),
            "profit_factor": None if pf == float("inf") else pf,
            "avg_rr": stats.avg_rr,
            "max_drawdown_r": stats.max_drawdown_r,
            "total_r": stats.total_r,
        },
        "equity_curve": _equity_curve(trades),
        "trades": [
            {
                "direction": t.direction,
                "entry": t.entry,
                "exit": t.exit_price,
                "r": t.r_multiple,
                "outcome": t.outcome,
            }
            for t in trades[-30:]
        ],
    }


def _equity_curve(trades) -> list[dict[str, float]]:
    """Courbe cumulée de R pour le graphique de backtest."""
    cum = 0.0
    out = [{"i": 0, "r": 0.0}]
    for idx, t in enumerate(trades, start=1):
        cum += t.r_multiple
        out.append({"i": idx, "r": round(cum, 3)})
    return out


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Journal de trades — écritures LOCALES uniquement (jamais un broker).
from dataclasses import asdict

from src.journal import store as journal_store


def journal_view() -> dict[str, Any]:
    return {
        "trades": journal_store.list_trades(),
        "expectancy": asdict(journal_store.expectancy()),
    }


def journal_add(payload: dict[str, Any]) -> dict[str, Any]:
    trade = journal_store.add_trade(payload)
    return asdict(trade)


def journal_close(trade_id: str, exit_price: float) -> dict[str, Any]:
    trade = journal_store.close_trade(trade_id, exit_price)
    return asdict(trade)


def journal_delete(trade_id: str) -> bool:
    return journal_store.delete_trade(trade_id)


# --------------------------------------------------------------------------
def portfolio() -> dict[str, Any]:
    """Vue portefeuille consolidée (lecture seule). Démo : brokers absents."""
    from src.connectors.aggregator import aggregate

    view = aggregate()
    return {
        "total_equity": view.total_equity,
        "available_brokers": view.available_brokers,
        "unavailable_brokers": view.unavailable_brokers,
        "balances": [
            {"broker": b.broker, "currency": b.currency, "cash": b.cash, "equity": b.equity}
            for b in view.balances
        ],
        "positions": [
            {
                "broker": p.broker,
                "symbol": p.symbol,
                "quantity": p.quantity,
                "unrealized_pnl": p.unrealized_pnl,
            }
            for p in view.positions
        ],
        "demo_mode": not view.available_brokers,
    }

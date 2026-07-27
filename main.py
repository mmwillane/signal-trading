"""Point d'entrée — MODE DÉMO par défaut.

Par défaut : aucune connexion broker. On lit des données publiques
(yfinance), on récupère quelques news, on calcule les indicateurs et on
génère des propositions d'ordre à exécuter MANUELLEMENT.

Le portefeuille broker (lecture seule) ne s'affiche que si vous passez
--brokers ET avez renseigné des clés read-only dans .env.

Usage :
    python main.py                 # démo : propositions seules
    python main.py --brokers       # + vue portefeuille lecture seule
    python main.py --no-news       # sans sentiment news
"""

from __future__ import annotations

import argparse

from src.security.console import enable_utf8

enable_utf8()  # avant tout affichage (consoles Windows cp1252)

from src.analysis.analyzer import evaluate_latest
from src.data.market_data import get_history
from src.knowledge import trading_rules as tr
from src.news.news_feed import fetch_news, filter_for_symbol
from src.news.sentiment import score_news
from src.proposal.order_proposal import build_proposal
from src.security.env import ConfigError, load_settings
from src.security.safe_logging import get_logger

log = get_logger("main")

BANNER = """
==============================================================
  ASSISTANT DE TRADING — AIDE À LA DÉCISION, LECTURE SEULE
  Ne passe/modifie/annule JAMAIS d'ordre. Exécution manuelle.
  Aucune prédiction, aucune garantie de résultat.
==============================================================
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Assistant de trading (lecture seule)")
    parser.add_argument("--brokers", action="store_true", help="Afficher le portefeuille (lecture seule)")
    parser.add_argument("--no-news", action="store_true", help="Ignorer le sentiment news")
    args = parser.parse_args()

    print(BANNER)

    try:
        settings = load_settings()
    except ConfigError as exc:
        log.error("Configuration invalide :\n%s", exc)
        return 1

    print(f"Capital : {settings.capital:.2f} {settings.base_currency} | "
          f"Risque/trade : {settings.risk_per_trade:.1%} "
          f"({settings.risk_amount():.2f} {settings.base_currency})")
    print(f"Watchlist : {', '.join(settings.watchlist)}\n")
    print("Principes appliqués :")
    print(tr.rules_summary(), "\n")

    # News globales récupérées une fois, filtrées par instrument ensuite.
    all_news = [] if args.no_news else fetch_news()

    proposals = 0
    for symbol in settings.watchlist:
        df = get_history(symbol, period="1y", interval="1d")
        if df is None or len(df) < tr.TREND_FILTER_WINDOW:
            print(f"[{symbol}] données insuffisantes — ignoré.")
            continue

        sentiment_score = 0.0
        if all_news:
            relevant = filter_for_symbol(all_news, symbol)
            sentiment_score = score_news(relevant).score

        signal = evaluate_latest(df, sentiment_score)
        if not signal.has_setup:
            print(f"[{symbol}] pas de setup clair — aucune proposition. "
                  f"({signal.reasons[0]})")
            continue

        proposal = build_proposal(
            symbol, signal,
            capital=settings.capital,
            risk_per_trade=settings.risk_per_trade,
            sentiment_score=sentiment_score,
            allow_fractional=settings.asset_class == "crypto",
        )
        if proposal is None:
            print(f"[{symbol}] setup rejeté (R/R insuffisant ou taille nulle).")
            continue

        print("\n" + proposal.render() + "\n")
        proposals += 1

    if proposals == 0:
        print("\nAucune proposition conforme aujourd'hui. "
              "Ne rien faire est une décision valable.")

    if args.brokers:
        _show_portfolio()

    return 0


def _show_portfolio() -> None:
    """Vue portefeuille lecture seule — importée seulement si demandée."""
    from src.connectors.aggregator import aggregate

    print("\n" + aggregate().render())


if __name__ == "__main__":
    raise SystemExit(main())

"""Scoring de sentiment des news.

Choix expliqué :
- VADER (vaderSentiment) : lexique orienté texte court, sans téléchargement
  de modèle ni GPU, déterministe et rapide. Suffisant pour pondérer un
  biais haussier/baissier — ce n'est PAS une prédiction de prix.
- Repli : si VADER est absent, on renvoie un score neutre (0.0) plutôt
  que de planter. Le sentiment devient alors simplement non contributif.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..security.safe_logging import get_logger
from .news_feed import NewsItem

log = get_logger("sentiment")


@dataclass(frozen=True)
class SentimentResult:
    score: float            # -1 (très négatif) .. +1 (très positif)
    label: str              # "positif" | "neutre" | "négatif"
    n_items: int

    @property
    def is_meaningful(self) -> bool:
        return self.n_items > 0 and abs(self.score) >= 0.15


def score_news(items: list[NewsItem]) -> SentimentResult:
    """Agrège le sentiment sur une liste de news."""
    if not items:
        return SentimentResult(0.0, "neutre", 0)

    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    except ImportError:
        log.warning("vaderSentiment absent : sentiment neutralisé.")
        return SentimentResult(0.0, "neutre", len(items))

    analyzer = SentimentIntensityAnalyzer()
    scores = [
        analyzer.polarity_scores(f"{it.title}. {it.summary}")["compound"]
        for it in items
    ]
    avg = sum(scores) / len(scores)
    return SentimentResult(round(avg, 3), _label(avg), len(items))


def _label(score: float) -> str:
    if score >= 0.15:
        return "positif"
    if score <= -0.15:
        return "négatif"
    return "neutre"

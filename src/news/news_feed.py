"""Récupération de news via flux RSS de sources financières fiables.

Choix expliqué :
- On se limite volontairement à QUELQUES sources solides (pas de
  ratissage massif) : réduit le bruit, la charge réseau et le risque
  d'ingérer du contenu douteux.
- RSS par défaut = zéro clé requise, fonctionne en mode démo.
- Chaque champ externe passe par sanitize.* : on ne fait jamais confiance
  au flux.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..security.safe_logging import get_logger
from ..security.sanitize import clean_text, safe_url

log = get_logger("news")

# Sources générales fiables + thèmes macro (taux, inflation, banques
# centrales, géopolitique). Ajoutez/retirez ici en connaissance de cause.
DEFAULT_FEEDS: dict[str, str] = {
    "Reuters Business": "https://feeds.reuters.com/reuters/businessNews",
    "CNBC Markets": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "MarketWatch Top": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "Fed Press": "https://www.federalreserve.gov/feeds/press_all.xml",
}

# Mots-clés macro pour taguer une news comme pertinente au niveau système.
_MACRO_THEMES = {
    "taux": ("rate", "rates", "yield", "fed funds", "hike", "cut"),
    "inflation": ("inflation", "cpi", "ppi", "deflation"),
    "banques centrales": ("fed", "ecb", "central bank", "boe", "boj", "powell"),
    "géopolitique": ("war", "sanction", "election", "conflict", "tariff"),
}


@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    summary: str
    url: str | None
    macro_themes: tuple[str, ...]


def fetch_news(
    feeds: dict[str, str] | None = None,
    *,
    max_per_feed: int = 10,
) -> list[NewsItem]:
    """Récupère et assainit les news des flux RSS. Dégrade proprement."""
    try:
        import feedparser
    except ImportError:
        log.error("feedparser non installé : pip install -r requirements.txt")
        return []

    feeds = feeds or DEFAULT_FEEDS
    items: list[NewsItem] = []
    for source, url in feeds.items():
        if safe_url(url) is None:
            log.warning("URL de flux invalide ignorée : %s", source)
            continue
        try:
            parsed = feedparser.parse(url)
        except Exception as exc:  # feedparser tolère mais on borne le risque
            log.warning("Flux illisible (%s) : %s", source, type(exc).__name__)
            continue

        for entry in parsed.entries[:max_per_feed]:
            title = clean_text(getattr(entry, "title", ""), max_len=300)
            if not title:
                continue
            summary = clean_text(getattr(entry, "summary", ""), max_len=1000)
            items.append(
                NewsItem(
                    source=source,
                    title=title,
                    summary=summary,
                    url=safe_url(getattr(entry, "link", None)),
                    macro_themes=_detect_themes(f"{title} {summary}"),
                )
            )
    log.info("News récupérées : %d éléments", len(items))
    return items


def filter_for_symbol(items: list[NewsItem], symbol: str, names: tuple[str, ...] = ()) -> list[NewsItem]:
    """Filtre les news mentionnant le symbole ou un de ses noms usuels."""
    needles = {symbol.lower(), *(n.lower() for n in names)}
    out = []
    for it in items:
        blob = f"{it.title} {it.summary}".lower()
        if any(n in blob for n in needles if n):
            out.append(it)
    return out


def _detect_themes(text: str) -> tuple[str, ...]:
    low = text.lower()
    return tuple(
        theme
        for theme, kws in _MACRO_THEMES.items()
        if any(k in low for k in kws)
    )

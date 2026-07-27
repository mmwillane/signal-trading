"""Assainissement des entrées externes (réponses API, news).

Principe : NE JAMAIS faire confiance à une réponse réseau. Toute donnée
externe passe par ces fonctions avant traitement. On borne les types, on
nettoie le texte, on rejette les valeurs numériques aberrantes.
"""

from __future__ import annotations

import math
import re
import unicodedata

# Symboles autorisés : lettres, chiffres, tirets, points, séparateurs FX.
_SYMBOL_RE = re.compile(r"[^A-Za-z0-9.\-/=^]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_symbol(raw: str) -> str:
    """Normalise un ticker : majuscules, caractères sûrs uniquement."""
    if not isinstance(raw, str):
        raise ValueError("Le symbole doit être une chaîne.")
    cleaned = _SYMBOL_RE.sub("", raw.strip().upper())
    if not cleaned or len(cleaned) > 20:
        raise ValueError(f"Symbole invalide après nettoyage : {raw!r}")
    return cleaned


def clean_text(raw: object, max_len: int = 2000) -> str:
    """Nettoie un texte externe (titre/résumé de news).

    - force un type str, sinon chaîne vide ;
    - retire les caractères de contrôle ;
    - normalise l'Unicode et borne la longueur (anti-abus mémoire).
    """
    if not isinstance(raw, str):
        return ""
    text = unicodedata.normalize("NFKC", raw)
    text = _CONTROL_RE.sub("", text).strip()
    return text[:max_len]


def safe_float(value: object, *, allow_negative: bool = True) -> float | None:
    """Convertit une valeur externe en float fini, sinon None.

    Rejette NaN/inf (fréquents dans les réponses API partielles) qui
    corrompraient silencieusement les indicateurs.
    """
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    if not allow_negative and result < 0:
        return None
    return result


def safe_url(raw: object) -> str | None:
    """Valide une URL de source de news (http/https uniquement)."""
    if not isinstance(raw, str):
        return None
    url = raw.strip()
    if url.startswith(("http://", "https://")) and len(url) <= 2048:
        return url
    return None

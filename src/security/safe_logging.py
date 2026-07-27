"""Logging avec masquage automatique des secrets.

Choix expliqué :
- Un filtre logging intercepte CHAQUE message et masque les motifs
  ressemblant à des clés/secrets. Même si un développeur logue par erreur
  un dict de config, la valeur sensible est caviardée avant écriture.
- On ne logue jamais volontairement de solde, de clé ou d'identifiant de
  compte ; ce filtre est la deuxième ligne de défense.
"""

from __future__ import annotations

import logging
import re

# Motifs de clés à masquer dans les messages (JSON, kwargs, "key=...").
_SECRET_KEY_HINTS = re.compile(
    r"(?i)(api[_-]?key|api[_-]?secret|secret|token|password|passwd|"
    r"access[_-]?key|private[_-]?key|authorization)"
)
# Capture "clef: valeur" ou "clef=valeur" et remplace la valeur.
_KV_PATTERN = re.compile(
    r"(?i)\b([\w-]*(?:key|secret|token|password|passwd|authorization)[\w-]*)"
    r"\s*[=:]\s*['\"]?([^\s,'\"}]+)"
)


class SecretRedactionFilter(logging.Filter):
    """Remplace les valeurs de secrets détectées par [REDACTED]."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if _SECRET_KEY_HINTS.search(msg):
            record.msg = _KV_PATTERN.sub(r"\1=[REDACTED]", msg)
            record.args = ()  # message déjà rendu ; évite un double formatage
        return True


def get_logger(name: str) -> logging.Logger:
    """Renvoie un logger configuré une seule fois, avec caviardage actif."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        handler.addFilter(SecretRedactionFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger

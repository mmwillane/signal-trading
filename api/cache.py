"""Cache TTL en mémoire.

But : éviter de re-télécharger yfinance / re-parser les news à chaque
requête HTTP. Un simple cache clé -> (valeur, expiration) suffit pour un
usage personnel. Thread-safe via un verrou (uvicorn peut servir en
plusieurs tâches).
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

_store: dict[str, tuple[float, Any]] = {}
_lock = threading.Lock()


def get_or_set(key: str, ttl: float, producer: Callable[[], Any]) -> Any:
    """Renvoie la valeur en cache si fraîche, sinon la (re)calcule.

    `producer` n'est appelé qu'en cas d'absence/expiration. Les erreurs de
    `producer` ne sont pas mises en cache.
    """
    now = time.time()
    with _lock:
        entry = _store.get(key)
        if entry is not None and entry[0] > now:
            return entry[1]

    value = producer()  # hors verrou : appel réseau potentiellement long

    with _lock:
        _store[key] = (now + ttl, value)
    return value


def invalidate(key: str) -> None:
    """Supprime une entrée du cache (p. ex. pour ne pas mémoriser un échec)."""
    with _lock:
        _store.pop(key, None)


def clear() -> None:
    with _lock:
        _store.clear()

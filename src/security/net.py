"""Accès réseau robuste : timeouts, retries, backoff exponentiel.

Choix expliqué :
- Toute requête sortante a un timeout obligatoire (jamais d'attente
  infinie qui figerait l'outil).
- On réessaie uniquement les erreurs transitoires (429, 5xx, timeouts,
  erreurs de connexion), avec un backoff exponentiel + jitter pour ne pas
  marteler une API en limite de taux.
- On respecte l'en-tête Retry-After quand le serveur l'envoie.
"""

from __future__ import annotations

import random
import time
from typing import Any

import requests

from .safe_logging import get_logger

log = get_logger("net")

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
    max_retries: int = 4,
    backoff_base: float = 0.75,
) -> Any | None:
    """GET JSON avec retries/backoff. Renvoie l'objet décodé ou None.

    Ne lève pas : en cas d'échec définitif on renvoie None pour que
    l'appelant dégrade proprement plutôt que de planter.
    """
    last_error: str = "inconnue"
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = f"réseau ({type(exc).__name__})"
        else:
            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError:
                    log.warning("Réponse non-JSON depuis %s", _host(url))
                    return None
            if resp.status_code not in _RETRYABLE_STATUS:
                # 4xx non transitoire (clé invalide, 404...) : inutile de réessayer.
                log.warning("HTTP %s depuis %s", resp.status_code, _host(url))
                return None
            last_error = f"HTTP {resp.status_code}"
            retry_after = _parse_retry_after(resp)
            if retry_after is not None:
                time.sleep(retry_after)
                continue

        # Backoff exponentiel + jitter avant la prochaine tentative.
        if attempt < max_retries - 1:
            delay = backoff_base * (2**attempt) + random.uniform(0, 0.4)
            time.sleep(delay)

    log.warning("Échec définitif GET %s (%s)", _host(url), last_error)
    return None


def _parse_retry_after(resp: requests.Response) -> float | None:
    raw = resp.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return min(float(raw), 30.0)  # borne pour ne pas bloquer trop longtemps
    except ValueError:
        return None


def _host(url: str) -> str:
    """N'affiche que l'hôte dans les logs (jamais les query params/clés)."""
    try:
        return url.split("/")[2]
    except IndexError:
        return "?"

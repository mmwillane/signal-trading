"""Chargement et validation stricte de la configuration.

Choix expliqué :
- On centralise TOUTE lecture de secret ici. Aucun autre module ne lit
  os.environ directement, ce qui rend l'audit trivial ("où sont les
  secrets ?" -> un seul fichier).
- On échoue tôt et clairement : si une variable obligatoire manque, on
  lève ConfigError avec un message actionnable plutôt que de planter
  plus tard avec une KeyError obscure.
- Les valeurs de secret ne sont jamais renvoyées dans un message
  d'erreur ni un __repr__.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError as exc:  # pragma: no cover - dépendance obligatoire
    raise SystemExit(
        "python-dotenv manquant. Installez les dépendances : "
        "pip install -r requirements.txt"
    ) from exc


class ConfigError(RuntimeError):
    """Erreur de configuration destinée à l'utilisateur (pas de secret dedans)."""


# Variables strictement obligatoires pour le mode démo (aucun broker requis).
_REQUIRED = ("CAPITAL", "RISK_PER_TRADE", "WATCHLIST")


@dataclass(frozen=True)
class Settings:
    """Configuration validée et typée, sans aucun secret broker exposé."""

    capital: float
    risk_per_trade: float
    base_currency: str
    watchlist: tuple[str, ...]
    asset_class: str
    newsapi_key: str | None = field(default=None, repr=False)  # jamais affiché

    def risk_amount(self) -> float:
        """Montant en devise risqué par trade (capital * risque %)."""
        return round(self.capital * self.risk_per_trade, 2)


def broker_secret(name: str) -> str | None:
    """Accès contrôlé aux secrets broker. Renvoie None si absent.

    Point d'entrée UNIQUE pour lire un secret : les adaptateurs passent
    tous par ici, ce qui évite tout os.environ dispersé et garde la
    surface de secret minimale et auditable.
    """
    value = os.environ.get(name, "").strip()
    return value or None


def load_settings(dotenv_path: str | Path | None = None) -> Settings:
    """Charge .env, valide les champs obligatoires, renvoie Settings.

    Lève ConfigError (message clair) si une variable manque ou est invalide.
    """
    # override=False : une variable déjà présente dans l'environnement du
    # système gagne sur le .env (utile en CI/conteneur).
    load_dotenv(dotenv_path=dotenv_path, override=False)

    missing = [name for name in _REQUIRED if not os.environ.get(name, "").strip()]
    if missing:
        raise ConfigError(
            "Variables obligatoires manquantes dans .env : "
            + ", ".join(missing)
            + ".\nCopiez .env.example vers .env et renseignez-les."
        )

    try:
        capital = float(os.environ["CAPITAL"])
        risk = float(os.environ["RISK_PER_TRADE"])
    except ValueError as exc:
        raise ConfigError(
            "CAPITAL et RISK_PER_TRADE doivent être numériques "
            "(ex. CAPITAL=10000, RISK_PER_TRADE=0.01)."
        ) from exc

    if capital <= 0:
        raise ConfigError("CAPITAL doit être strictement positif.")
    if not 0 < risk <= 0.1:
        # Garde-fou : plus de 10 % du capital par trade est un signal d'erreur.
        raise ConfigError(
            "RISK_PER_TRADE doit être dans ]0, 0.1]. "
            "Ex. 0.01 pour 1 % du capital par trade."
        )

    watchlist = tuple(
        s.strip().upper()
        for s in os.environ["WATCHLIST"].split(",")
        if s.strip()
    )
    if not watchlist:
        raise ConfigError("WATCHLIST est vide. Renseignez au moins un instrument.")

    return Settings(
        capital=capital,
        risk_per_trade=risk,
        base_currency=os.environ.get("BASE_CURRENCY", "USD").strip().upper(),
        watchlist=watchlist,
        asset_class=os.environ.get("ASSET_CLASS", "stocks").strip().lower(),
        newsapi_key=broker_secret("NEWSAPI_KEY"),
    )

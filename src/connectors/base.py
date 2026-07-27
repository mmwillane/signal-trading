"""Interface commune des connecteurs brokers — LECTURE SEULE.

GARANTIE DE CONCEPTION (à lire) :
- Cette classe abstraite ne déclare QUE des méthodes de lecture :
  get_balance, get_positions, get_order_history, get_account_info.
- Il n'existe AUCUNE méthode place_order / cancel_order / modify_order,
  ni dans l'interface ni dans les adaptateurs. Le connecteur est
  structurellement incapable de trader.
- Toute tentative future d'ajouter une méthode d'écriture doit être
  refusée en revue de code. Un test (tests/test_readonly.py) échoue si
  un nom de méthode d'exécution apparaît sur un connecteur.

Chaque adaptateur concret traduit l'API d'un broker vers ces DTO neutres.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Balance:
    broker: str
    currency: str
    cash: float
    equity: float            # cash + valeur des positions


@dataclass(frozen=True)
class Position:
    broker: str
    symbol: str
    quantity: float
    avg_price: float
    market_value: float
    unrealized_pnl: float


@dataclass(frozen=True)
class OrderRecord:
    """Historique en lecture seule d'un ordre DÉJÀ passé par l'utilisateur."""

    broker: str
    symbol: str
    side: str
    quantity: float
    price: float
    status: str
    timestamp: str


@dataclass(frozen=True)
class AccountInfo:
    broker: str
    account_id_masked: str   # jamais l'ID complet en clair
    account_type: str
    extra: dict[str, str] = field(default_factory=dict)


class ReadOnlyBrokerConnector(abc.ABC):
    """Contrat commun. Uniquement des lectures — par conception."""

    #: Nom lisible du broker (renseigné par l'adaptateur).
    name: str = "abstract"

    @abc.abstractmethod
    def is_available(self) -> bool:
        """True si le SDK est installé ET les clés (read-only) présentes."""

    @abc.abstractmethod
    def get_balance(self) -> Balance | None:
        """Solde/équité. None si indisponible (sans planter)."""

    @abc.abstractmethod
    def get_positions(self) -> list[Position]:
        """Positions ouvertes. Liste vide si aucune/indisponible."""

    @abc.abstractmethod
    def get_order_history(self, limit: int = 50) -> list[OrderRecord]:
        """Historique des ordres passés (lecture). Liste vide si indispo."""

    @abc.abstractmethod
    def get_account_info(self) -> AccountInfo | None:
        """Métadonnées de compte, identifiants masqués."""


def mask_account_id(account_id: str) -> str:
    """Masque un identifiant de compte : ne garde que les 4 derniers."""
    account_id = str(account_id)
    if len(account_id) <= 4:
        return "****"
    return "****" + account_id[-4:]

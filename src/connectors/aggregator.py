"""Agrégation multi-brokers en une vue unifiée — LECTURE SEULE.

Rassemble solde total et positions consolidées de tous les connecteurs
disponibles. Un broker indisponible (SDK absent, clés manquantes, API
restreinte) est SIGNALÉ, jamais une cause de crash.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..security.safe_logging import get_logger
from .base import Balance, Position, ReadOnlyBrokerConnector
from .alpaca import AlpacaConnector
from .ccxt_broker import BinanceConnector, KrakenConnector
from .ibkr import IBKRConnector
from .oanda import OandaConnector

log = get_logger("aggregator")


def default_connectors() -> list[ReadOnlyBrokerConnector]:
    """Instancie tous les adaptateurs connus (aucun n'est requis)."""
    return [
        AlpacaConnector(),
        OandaConnector(),
        BinanceConnector(),
        KrakenConnector(),
        IBKRConnector(),
    ]


@dataclass
class PortfolioView:
    total_equity: float = 0.0
    balances: list[Balance] = field(default_factory=list)
    positions: list[Position] = field(default_factory=list)
    available_brokers: list[str] = field(default_factory=list)
    unavailable_brokers: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = ["=== Vue portefeuille consolidée (lecture seule) ==="]
        if self.available_brokers:
            lines.append("Brokers connectés : " + ", ".join(self.available_brokers))
        if self.unavailable_brokers:
            lines.append(
                "Brokers non connectés (ignorés) : "
                + ", ".join(self.unavailable_brokers)
            )
        if not self.balances:
            lines.append("Aucun compte broker en lecture — mode démo actif.")
            return "\n".join(lines)

        lines.append(f"Équité totale : {self.total_equity:.2f}")
        for b in self.balances:
            lines.append(f"  {b.broker:<22} cash={b.cash:.2f}  équité={b.equity:.2f}")
        if self.positions:
            lines.append("Positions consolidées :")
            for p in self.positions:
                lines.append(
                    f"  {p.broker:<12} {p.symbol:<12} qty={p.quantity:g} "
                    f"PnL={p.unrealized_pnl:+.2f}"
                )
        return "\n".join(lines)


def aggregate(
    connectors: list[ReadOnlyBrokerConnector] | None = None,
) -> PortfolioView:
    """Interroge chaque connecteur disponible et consolide."""
    connectors = connectors or default_connectors()
    view = PortfolioView()

    for c in connectors:
        try:
            available = c.is_available()
        except Exception as exc:  # un adaptateur ne doit jamais tout casser
            log.warning("%s : vérification échouée (%s)", c.name, type(exc).__name__)
            available = False

        if not available:
            view.unavailable_brokers.append(c.name)
            continue

        view.available_brokers.append(c.name)
        balance = c.get_balance()
        if balance is not None:
            view.balances.append(balance)
            view.total_equity += balance.equity
        view.positions.extend(c.get_positions())

    view.total_equity = round(view.total_equity, 2)
    return view

"""Adaptateur Interactive Brokers — LECTURE SEULE.

Particularité IBKR : pas de clé API dans un .env. On se connecte à une
passerelle locale (IB Gateway ou TWS) via ib_insync. Pour la lecture seule,
lancez la passerelle en session « read-only API » (option cochable dans
TWS/Gateway : Configuration > API > Read-Only API). Ainsi, même le
protocole refuse tout ordre au niveau de la passerelle.

On n'utilise que accountSummary / positions / trades. Aucune méthode
placeOrder n'est appelée.
"""

from __future__ import annotations

from ..security.env import broker_secret
from ..security.safe_logging import get_logger
from ..security.sanitize import safe_float
from .base import (
    AccountInfo,
    Balance,
    OrderRecord,
    Position,
    ReadOnlyBrokerConnector,
    mask_account_id,
)

log = get_logger("connector.ibkr")


class IBKRConnector(ReadOnlyBrokerConnector):
    name = "Interactive Brokers"

    def __init__(self) -> None:
        self._host = broker_secret("IBKR_HOST") or "127.0.0.1"
        self._port = int(broker_secret("IBKR_PORT") or "4001")
        self._client_id = int(broker_secret("IBKR_CLIENT_ID") or "1")
        self._ib = None

    def _connect(self):
        if self._ib is not None:
            return self._ib
        try:
            from ib_insync import IB
        except ImportError:
            log.info("ib_insync non installé : IBKR indisponible.")
            return None
        ib = IB()
        try:
            ib.connect(
                self._host,
                self._port,
                clientId=self._client_id,
                timeout=8,
                readonly=True,  # défense en profondeur côté client
            )
        except Exception as exc:
            log.info(
                "Passerelle IBKR injoignable (%s). Lancez IB Gateway/TWS en "
                "mode read-only.",
                type(exc).__name__,
            )
            return None
        self._ib = ib
        return ib

    def is_available(self) -> bool:
        ib = self._connect()
        return ib is not None and ib.isConnected()

    def get_balance(self) -> Balance | None:
        ib = self._connect()
        if ib is None:
            return None
        try:
            summary = {v.tag: v.value for v in ib.accountSummary()}
        except Exception as exc:
            log.warning("IBKR balance: %s", type(exc).__name__)
            return None
        return Balance(
            broker=self.name,
            currency=summary.get("Currency", "USD"),
            cash=safe_float(summary.get("TotalCashValue")) or 0.0,
            equity=safe_float(summary.get("NetLiquidation")) or 0.0,
        )

    def get_positions(self) -> list[Position]:
        ib = self._connect()
        if ib is None:
            return []
        out: list[Position] = []
        try:
            for p in ib.positions():
                out.append(
                    Position(
                        broker=self.name,
                        symbol=str(getattr(p.contract, "symbol", "?")),
                        quantity=safe_float(p.position) or 0.0,
                        avg_price=safe_float(p.avgCost) or 0.0,
                        market_value=0.0,
                        unrealized_pnl=0.0,
                    )
                )
        except Exception as exc:
            log.warning("IBKR positions: %s", type(exc).__name__)
        return out

    def get_order_history(self, limit: int = 50) -> list[OrderRecord]:
        ib = self._connect()
        if ib is None:
            return []
        out: list[OrderRecord] = []
        try:
            for t in ib.trades()[:limit]:
                out.append(
                    OrderRecord(
                        broker=self.name,
                        symbol=str(getattr(t.contract, "symbol", "?")),
                        side=str(getattr(t.order, "action", "?")).lower(),
                        quantity=safe_float(getattr(t.order, "totalQuantity", None)) or 0.0,
                        price=safe_float(getattr(t.orderStatus, "avgFillPrice", None)) or 0.0,
                        status=str(getattr(t.orderStatus, "status", "?")),
                        timestamp="",
                    )
                )
        except Exception as exc:
            log.warning("IBKR order_history: %s", type(exc).__name__)
        return out

    def get_account_info(self) -> AccountInfo | None:
        ib = self._connect()
        if ib is None:
            return None
        accounts = ib.managedAccounts() if hasattr(ib, "managedAccounts") else []
        acct_id = accounts[0] if accounts else ""
        return AccountInfo(
            broker=self.name,
            account_id_masked=mask_account_id(acct_id),
            account_type="ibkr-readonly-gateway",
        )

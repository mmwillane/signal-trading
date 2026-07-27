"""Adaptateur Alpaca — LECTURE SEULE (actions US / crypto).

SDK : alpaca-py (import paresseux). On n'utilise que TradingClient en
lecture (get_account, get_all_positions, get_orders). La méthode
submit_order existe dans le SDK ; on ne l'appelle jamais et on ne
l'expose pas.

Sécurité : générez une clé « read only » dans le tableau de bord Alpaca.
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

log = get_logger("connector.alpaca")


class AlpacaConnector(ReadOnlyBrokerConnector):
    name = "Alpaca"

    def __init__(self) -> None:
        self._key = broker_secret("ALPACA_API_KEY")
        self._secret = broker_secret("ALPACA_API_SECRET")
        self._paper = (broker_secret("ALPACA_PAPER") or "true").lower() != "false"
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from alpaca.trading.client import TradingClient
        except ImportError:
            log.info("alpaca-py non installé : Alpaca indisponible.")
            return None
        if not (self._key and self._secret):
            log.info("Clés Alpaca absentes : connecteur ignoré.")
            return None
        self._client = TradingClient(self._key, self._secret, paper=self._paper)
        return self._client

    def is_available(self) -> bool:
        return self._get_client() is not None

    def get_balance(self) -> Balance | None:
        client = self._get_client()
        if client is None:
            return None
        try:
            acct = client.get_account()
        except Exception as exc:
            log.warning("Alpaca get_account: %s", type(exc).__name__)
            return None
        return Balance(
            broker=self.name,
            currency=str(getattr(acct, "currency", "USD")),
            cash=safe_float(getattr(acct, "cash", None)) or 0.0,
            equity=safe_float(getattr(acct, "equity", None)) or 0.0,
        )

    def get_positions(self) -> list[Position]:
        client = self._get_client()
        if client is None:
            return []
        try:
            raw = client.get_all_positions()
        except Exception as exc:
            log.warning("Alpaca positions: %s", type(exc).__name__)
            return []
        out: list[Position] = []
        for p in raw or []:
            out.append(
                Position(
                    broker=self.name,
                    symbol=str(getattr(p, "symbol", "?")),
                    quantity=safe_float(getattr(p, "qty", None)) or 0.0,
                    avg_price=safe_float(getattr(p, "avg_entry_price", None)) or 0.0,
                    market_value=safe_float(getattr(p, "market_value", None)) or 0.0,
                    unrealized_pnl=safe_float(getattr(p, "unrealized_pl", None)) or 0.0,
                )
            )
        return out

    def get_order_history(self, limit: int = 50) -> list[OrderRecord]:
        client = self._get_client()
        if client is None:
            return []
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus

            req = GetOrdersRequest(status=QueryOrderStatus.ALL, limit=limit)
            raw = client.get_orders(filter=req)
        except Exception as exc:
            log.warning("Alpaca order_history: %s", type(exc).__name__)
            return []
        out: list[OrderRecord] = []
        for o in raw or []:
            out.append(
                OrderRecord(
                    broker=self.name,
                    symbol=str(getattr(o, "symbol", "?")),
                    side=str(getattr(o, "side", "?")),
                    quantity=safe_float(getattr(o, "qty", None)) or 0.0,
                    price=safe_float(getattr(o, "filled_avg_price", None)) or 0.0,
                    status=str(getattr(o, "status", "?")),
                    timestamp=str(getattr(o, "submitted_at", "")),
                )
            )
        return out

    def get_account_info(self) -> AccountInfo | None:
        client = self._get_client()
        if client is None:
            return None
        try:
            acct = client.get_account()
        except Exception as exc:
            log.warning("Alpaca account_info: %s", type(exc).__name__)
            return None
        return AccountInfo(
            broker=self.name,
            account_id_masked=mask_account_id(str(getattr(acct, "id", ""))),
            account_type="paper" if self._paper else "live",
        )

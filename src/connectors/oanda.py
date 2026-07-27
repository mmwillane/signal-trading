"""Adaptateur OANDA — LECTURE SEULE (forex / CFD).

SDK : oandapyV20 (import paresseux). On n'utilise que des endpoints de
lecture (AccountDetails, OpenPositions, TransactionList). Aucune requête
OrderCreate n'est jamais construite.

Sécurité : un token OANDA porte les droits du compte ; pour rester en
lecture, n'utilisez ce connecteur que pour consulter, et préférez un
compte « practice » pour l'exploration.
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

log = get_logger("connector.oanda")


class OandaConnector(ReadOnlyBrokerConnector):
    name = "OANDA"

    def __init__(self) -> None:
        self._token = broker_secret("OANDA_API_TOKEN")
        self._account = broker_secret("OANDA_ACCOUNT_ID")
        self._env = (broker_secret("OANDA_ENV") or "practice").lower()
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from oandapyV20 import API
        except ImportError:
            log.info("oandapyV20 non installé : OANDA indisponible.")
            return None
        if not (self._token and self._account):
            log.info("Identifiants OANDA absents : connecteur ignoré.")
            return None
        self._client = API(access_token=self._token, environment=self._env)
        return self._client

    def is_available(self) -> bool:
        return self._get_client() is not None

    def get_balance(self) -> Balance | None:
        client = self._get_client()
        if client is None:
            return None
        try:
            from oandapyV20.endpoints.accounts import AccountSummary

            req = AccountSummary(accountID=self._account)
            data = client.request(req)["account"]
        except Exception as exc:
            log.warning("OANDA get_balance: %s", type(exc).__name__)
            return None
        bal = safe_float(data.get("balance")) or 0.0
        nav = safe_float(data.get("NAV")) or bal
        return Balance(
            broker=self.name,
            currency=str(data.get("currency", "USD")),
            cash=round(bal, 2),
            equity=round(nav, 2),
        )

    def get_positions(self) -> list[Position]:
        client = self._get_client()
        if client is None:
            return []
        try:
            from oandapyV20.endpoints.positions import OpenPositions

            req = OpenPositions(accountID=self._account)
            raw = client.request(req).get("positions", [])
        except Exception as exc:
            log.warning("OANDA positions: %s", type(exc).__name__)
            return []
        out: list[Position] = []
        for p in raw:
            long_units = safe_float(p.get("long", {}).get("units")) or 0.0
            short_units = safe_float(p.get("short", {}).get("units")) or 0.0
            net = long_units + short_units
            if net == 0:
                continue
            pnl = safe_float(p.get("unrealizedPL")) or 0.0
            out.append(
                Position(
                    broker=self.name,
                    symbol=str(p.get("instrument", "?")),
                    quantity=round(net, 4),
                    avg_price=0.0,
                    market_value=0.0,
                    unrealized_pnl=round(pnl, 2),
                )
            )
        return out

    def get_order_history(self, limit: int = 50) -> list[OrderRecord]:
        client = self._get_client()
        if client is None:
            return []
        try:
            from oandapyV20.endpoints.transactions import TransactionList

            req = TransactionList(accountID=self._account)
            data = client.request(req)
        except Exception as exc:
            log.warning("OANDA order_history: %s", type(exc).__name__)
            return []
        # TransactionList renvoie des pages ; on reste minimal et prudent.
        records = data.get("transactions", []) if isinstance(data, dict) else []
        out: list[OrderRecord] = []
        for t in records[:limit]:
            out.append(
                OrderRecord(
                    broker=self.name,
                    symbol=str(t.get("instrument", "?")),
                    side="buy" if (safe_float(t.get("units")) or 0) >= 0 else "sell",
                    quantity=abs(safe_float(t.get("units")) or 0.0),
                    price=safe_float(t.get("price")) or 0.0,
                    status=str(t.get("type", "?")),
                    timestamp=str(t.get("time", "")),
                )
            )
        return out

    def get_account_info(self) -> AccountInfo | None:
        if not self.is_available():
            return None
        return AccountInfo(
            broker=self.name,
            account_id_masked=mask_account_id(self._account or ""),
            account_type=self._env,
        )

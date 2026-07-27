"""Adaptateurs Binance & Kraken via ccxt — LECTURE SEULE.

ccxt couvre des dizaines de brokers crypto avec une API unifiée ; on
l'utilise pour Binance et Kraken. On n'appelle QUE des endpoints de
lecture (fetch_balance, fetch_positions, fetch_my_trades). ccxt expose
aussi create_order — on ne l'appelle jamais, et le test readonly interdit
son exposition sur nos connecteurs.

Rappel sécurité : créez la clé API avec la permission de LECTURE
uniquement (Binance : « Enable Reading » seul ; Kraken : « Query » seul).
Même si une clé avait des droits de trading, ce code ne les utiliserait
pas — mais une clé read-only est la bonne pratique de défense en profondeur.
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

log = get_logger("connector.ccxt")


class _CcxtReadOnly(ReadOnlyBrokerConnector):
    """Base commune ccxt. Les sous-classes fixent name / exchange_id / clés."""

    exchange_id: str = ""
    _key_env: str = ""
    _secret_env: str = ""

    def __init__(self) -> None:
        self._key = broker_secret(self._key_env)
        self._secret = broker_secret(self._secret_env)
        self._client = None

    # --- disponibilité ---------------------------------------------------
    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import ccxt
        except ImportError:
            log.info("ccxt non installé : %s indisponible.", self.name)
            return None
        if not (self._key and self._secret):
            log.info("Clés %s absentes : connecteur ignoré.", self.name)
            return None
        exchange_cls = getattr(ccxt, self.exchange_id)
        # enableRateLimit : ccxt gère lui-même le throttling anti-429.
        self._client = exchange_cls(
            {
                "apiKey": self._key,
                "secret": self._secret,
                "enableRateLimit": True,
            }
        )
        return self._client

    def is_available(self) -> bool:
        return self._get_client() is not None

    # --- lectures --------------------------------------------------------
    def get_balance(self) -> Balance | None:
        client = self._get_client()
        if client is None:
            return None
        try:
            data = client.fetch_balance()
        except Exception as exc:  # ccxt : erreurs réseau/auth hétérogènes
            log.warning("%s fetch_balance: %s", self.name, type(exc).__name__)
            return None

        total = data.get("total", {}) if isinstance(data, dict) else {}
        # Équité approximée par le total en devise de cotation la plus liquide.
        cash = safe_float(total.get("USDT")) or safe_float(total.get("USD")) or 0.0
        return Balance(
            broker=self.name,
            currency="USD",
            cash=round(cash, 2),
            equity=round(cash, 2),
        )

    def get_positions(self) -> list[Position]:
        client = self._get_client()
        if client is None:
            return []
        positions: list[Position] = []
        try:
            balances = client.fetch_balance().get("total", {})
        except Exception as exc:
            log.warning("%s positions: %s", self.name, type(exc).__name__)
            return []
        # Sur spot, une "position" = un solde non nul d'un actif hors stable.
        for asset, amount in balances.items():
            qty = safe_float(amount)
            if not qty or asset in ("USD", "USDT", "USDC"):
                continue
            positions.append(
                Position(
                    broker=self.name,
                    symbol=f"{asset}-USD",
                    quantity=round(qty, 8),
                    avg_price=0.0,      # ccxt spot ne fournit pas de PRU fiable
                    market_value=0.0,
                    unrealized_pnl=0.0,
                )
            )
        return positions

    def get_order_history(self, limit: int = 50) -> list[OrderRecord]:
        client = self._get_client()
        if client is None:
            return []
        try:
            trades = client.fetch_my_trades(limit=limit)
        except Exception as exc:
            log.warning("%s order_history: %s", self.name, type(exc).__name__)
            return []
        out: list[OrderRecord] = []
        for t in trades or []:
            out.append(
                OrderRecord(
                    broker=self.name,
                    symbol=str(t.get("symbol", "?")),
                    side=str(t.get("side", "?")),
                    quantity=safe_float(t.get("amount")) or 0.0,
                    price=safe_float(t.get("price")) or 0.0,
                    status="filled",
                    timestamp=str(t.get("datetime", "")),
                )
            )
        return out

    def get_account_info(self) -> AccountInfo | None:
        if not self.is_available():
            return None
        return AccountInfo(
            broker=self.name,
            account_id_masked=mask_account_id(self._key or ""),
            account_type="spot",
        )


class BinanceConnector(_CcxtReadOnly):
    name = "Binance"
    exchange_id = "binance"
    _key_env = "BINANCE_API_KEY"
    _secret_env = "BINANCE_API_SECRET"


class KrakenConnector(_CcxtReadOnly):
    name = "Kraken"
    exchange_id = "kraken"
    _key_env = "KRAKEN_API_KEY"
    _secret_env = "KRAKEN_API_SECRET"

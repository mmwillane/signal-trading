"""Journal de trades — stockage local et calcul d'espérance.

PORTÉE (important) : ce module enregistre les trades que L'UTILISATEUR a
décidé de prendre et exécutés lui-même sur sa plateforme. Il n'exécute,
n'envoie ni ne modifie AUCUN ordre chez un broker. Ce sont des écritures
dans un simple fichier JSON local (`data/journal.json`).

Pourquoi un journal : c'est l'edge le plus sous-estimé des traders sérieux.
Noter chaque trade permet de mesurer l'ESPÉRANCE réelle (win rate × gain
moyen − perte moyenne) et de corriger, au lieu de naviguer à l'aveugle.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from ..security.safe_logging import get_logger
from ..security.sanitize import clean_symbol, clean_text, safe_float

log = get_logger("journal")

_ROOT = Path(__file__).resolve().parents[2]
_STORE_PATH = _ROOT / "data" / "journal.json"
_lock = threading.Lock()


class JournalError(ValueError):
    """Erreur de saisie du journal (message utilisateur, sans secret)."""


@dataclass
class Trade:
    id: str
    symbol: str
    direction: str            # "buy" | "sell"
    entry: float
    stop: float
    take_profit: float
    quantity: float
    risk_amount: float
    confidence: int
    status: str               # "open" | "closed"
    opened_at: str            # ISO date
    exit_price: float | None = None
    closed_at: str | None = None
    r_multiple: float | None = None
    notes: str = ""
    source: str = "suggestion"

    @property
    def risk_per_unit(self) -> float:
        return abs(self.entry - self.stop)


# --------------------------------------------------------------------------
def _now_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _load() -> list[dict[str, Any]]:
    if not _STORE_PATH.exists():
        return []
    try:
        with _STORE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Journal illisible (%s) — repart d'un journal vide.", type(exc).__name__)
        return []


def _save(rows: list[dict[str, Any]]) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _STORE_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    tmp.replace(_STORE_PATH)  # écriture atomique


# --------------------------------------------------------------------------
def add_trade(payload: dict[str, Any]) -> Trade:
    """Ajoute un trade au journal après validation stricte des entrées."""
    symbol = clean_symbol(str(payload.get("symbol", "")))
    direction = str(payload.get("direction", "")).lower()
    if direction not in ("buy", "sell"):
        raise JournalError("Sens invalide (attendu 'buy' ou 'sell').")

    entry = safe_float(payload.get("entry"), allow_negative=False)
    stop = safe_float(payload.get("stop"), allow_negative=False)
    tp = safe_float(payload.get("take_profit"), allow_negative=False)
    qty = safe_float(payload.get("quantity"), allow_negative=False)
    if entry is None or stop is None or qty is None or qty <= 0:
        raise JournalError("Entrée, stop et quantité doivent être des nombres positifs.")
    if entry == stop:
        raise JournalError("L'entrée et le stop ne peuvent pas être identiques.")

    trade = Trade(
        id=uuid.uuid4().hex[:12],
        symbol=symbol,
        direction=direction,
        entry=round(entry, 6),
        stop=round(stop, 6),
        take_profit=round(tp, 6) if tp is not None else 0.0,
        quantity=round(qty, 8),
        risk_amount=round(qty * abs(entry - stop), 2),
        confidence=int(safe_float(payload.get("confidence")) or 0),
        status="open",
        opened_at=str(payload.get("opened_at") or _now_date()),
        notes=clean_text(payload.get("notes", ""), max_len=500),
        source=str(payload.get("source") or "suggestion"),
    )

    with _lock:
        rows = _load()
        rows.append(asdict(trade))
        _save(rows)
    log.info("Trade journalisé : %s %s", trade.symbol, trade.direction)
    return trade


def close_trade(trade_id: str, exit_price: float, closed_at: str | None = None) -> Trade:
    """Clôture un trade et calcule son résultat en R (multiples de risque)."""
    exit_p = safe_float(exit_price, allow_negative=False)
    if exit_p is None:
        raise JournalError("Prix de sortie invalide.")

    with _lock:
        rows = _load()
        for row in rows:
            if row["id"] != trade_id:
                continue
            if row["status"] == "closed":
                raise JournalError("Ce trade est déjà clôturé.")
            entry, stop = row["entry"], row["stop"]
            risk = abs(entry - stop)
            long = row["direction"] == "buy"
            pnl = (exit_p - entry) if long else (entry - exit_p)
            row["exit_price"] = round(exit_p, 6)
            row["r_multiple"] = round(pnl / risk, 3) if risk else 0.0
            row["status"] = "closed"
            row["closed_at"] = str(closed_at or _now_date())
            _save(rows)
            return Trade(**row)
    raise JournalError("Trade introuvable.")


def delete_trade(trade_id: str) -> bool:
    with _lock:
        rows = _load()
        new_rows = [r for r in rows if r["id"] != trade_id]
        if len(new_rows) == len(rows):
            return False
        _save(new_rows)
    return True


def list_trades() -> list[dict[str, Any]]:
    with _lock:
        rows = _load()
    # Les plus récents d'abord.
    return sorted(rows, key=lambda r: r.get("opened_at", ""), reverse=True)


# --------------------------------------------------------------------------
@dataclass
class Expectancy:
    n_closed: int = 0
    n_open: int = 0
    win_rate: float = 0.0
    avg_win_r: float = 0.0
    avg_loss_r: float = 0.0       # négatif
    expectancy_r: float = 0.0     # gain moyen attendu par trade, en R
    profit_factor: float | None = None
    total_r: float = 0.0
    total_risk_amount: float = 0.0


def expectancy() -> Expectancy:
    """Calcule l'espérance réelle sur les trades clôturés."""
    rows = list_trades()
    closed = [r for r in rows if r["status"] == "closed" and r.get("r_multiple") is not None]
    n_open = sum(1 for r in rows if r["status"] == "open")

    if not closed:
        return Expectancy(n_closed=0, n_open=n_open)

    r_vals = [float(r["r_multiple"]) for r in closed]
    wins = [r for r in r_vals if r > 0]
    losses = [r for r in r_vals if r < 0]

    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    win_rate = len(wins) / len(closed)

    return Expectancy(
        n_closed=len(closed),
        n_open=n_open,
        win_rate=round(win_rate, 4),
        avg_win_r=round(sum(wins) / len(wins), 3) if wins else 0.0,
        avg_loss_r=round(sum(losses) / len(losses), 3) if losses else 0.0,
        expectancy_r=round(sum(r_vals) / len(r_vals), 3),
        profit_factor=round(gross_win / gross_loss, 2) if gross_loss > 0 else None,
        total_r=round(sum(r_vals), 2),
        total_risk_amount=round(sum(float(r["risk_amount"]) for r in closed), 2),
    )

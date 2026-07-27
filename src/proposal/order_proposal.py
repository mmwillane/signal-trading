"""Construction d'une proposition d'ordre complète et lisible.

RAPPEL DE CONCEPTION : cet objet est une PROPOSITION. Il ne contient aucun
lien vers un broker et aucune méthode d'envoi. C'est un plan de trade à
valider et exécuter MANUELLEMENT par l'utilisateur.

Améliorations math :
- Stop STRUCTUREL : placé au-delà du plus bas/haut récent (swing), borné par
  la volatilité (entre 0.8 et 3 ATR) pour ne pas être trop serré ni trop large.
- Objectif à R/R cible (>= MIN_RR) => asymétrie garantie.
- Règle de STOP SUIVEUR (trailing) fournie pour la gestion après +1R.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..analysis.analyzer import Signal
from ..knowledge import trading_rules as tr
from .position_sizing import PositionSize, size_position


@dataclass(frozen=True)
class OrderProposal:
    symbol: str
    direction: str           # "buy" | "sell"
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    size: PositionSize
    reasons: tuple[str, ...]
    sentiment: float
    confidence: int = 0
    adx: float = 0.0
    stop_basis: str = "structurel"   # "structurel" | "volatilité (borné)"
    trailing_rule: str = ""

    def render(self) -> str:
        """Rendu texte explicite, avec l'avertissement obligatoire."""
        arrow = "ACHAT" if self.direction == "buy" else "VENTE"
        lines = [
            f"┌─ PROPOSITION ({arrow}) — {self.symbol}  [confiance {self.confidence}/100]",
            f"│  Entrée      : {self.entry:.4f}",
            f"│  Stop loss   : {self.stop_loss:.4f}  ({self.stop_basis})",
            f"│  Take profit : {self.take_profit:.4f}",
            f"│  Ratio R/R   : {self.risk_reward:.2f}   ADX : {self.adx:.0f}",
            f"│  Quantité    : {self.size.quantity:g}  "
            f"(exposition {self.size.notional:.2f})",
            f"│  Risque      : {self.size.risk_amount:.2f} "
            f"si le stop est touché",
            f"│  Trailing    : {self.trailing_rule}",
            "│  Raisonnement :",
            *[f"│    • {r}" for r in self.reasons],
            "│  ⚠  Proposition à VALIDER et EXÉCUTER MANUELLEMENT.",
            "│     Aucune garantie de résultat. Ceci n'est pas un conseil.",
            "└" + "─" * 52,
        ]
        return "\n".join(lines)


def compute_stop(signal: Signal) -> tuple[float, float, str]:
    """Calcule le stop structurel borné. Renvoie (stop, distance, base)."""
    entry, atr = signal.close, signal.atr
    min_d, max_d = tr.STOP_MIN_ATR * atr, tr.STOP_MAX_ATR * atr

    if signal.direction == "buy":
        # Stop sous le support récent, avec une petite marge.
        struct = signal.swing_low - tr.STOP_ATR_BUFFER * atr
        raw_dist = entry - struct
        basis = "structurel (sous le support)"
    else:
        struct = signal.swing_high + tr.STOP_ATR_BUFFER * atr
        raw_dist = struct - entry
        basis = "structurel (au-dessus de la résistance)"

    # Bornage par la volatilité : ni trop serré (bruit) ni trop large (risque).
    if raw_dist < min_d:
        dist, basis = min_d, "volatilité (support trop proche, borné à 0.8 ATR)"
    elif raw_dist > max_d:
        dist, basis = max_d, "volatilité (support trop loin, borné à 3 ATR)"
    else:
        dist = raw_dist

    stop = entry - dist if signal.direction == "buy" else entry + dist
    return stop, dist, basis


def build_proposal(
    symbol: str,
    signal: Signal,
    *,
    capital: float,
    risk_per_trade: float,
    sentiment_score: float = 0.0,
    allow_fractional: bool = True,
) -> OrderProposal | None:
    """Transforme un Signal en proposition complète, ou None si non conforme."""
    if not signal.has_setup or signal.atr <= 0:
        return None

    entry = signal.close
    stop, stop_dist, basis = compute_stop(signal)
    if stop <= 0 or stop_dist <= 0:
        return None

    # Objectif à R/R cible : asymétrie garantie (>= MIN_RR).
    rr = max(tr.TARGET_RR, tr.MIN_RR)
    tp_dist = rr * stop_dist
    take_profit = entry + tp_dist if signal.direction == "buy" else entry - tp_dist

    size = size_position(
        capital=capital,
        risk_per_trade=risk_per_trade,
        entry=entry,
        stop=stop,
        allow_fractional=allow_fractional,
    )
    if size is None:
        return None

    trailing = (
        f"une fois +1R atteint, remonter le stop à {tr.TRAIL_ATR_MULT:g}× ATR "
        f"{'sous le plus haut' if signal.direction == 'buy' else 'au-dessus du plus bas'} "
        "pour verrouiller les gains."
    )

    return OrderProposal(
        symbol=symbol,
        direction=signal.direction,
        entry=round(entry, 4),
        stop_loss=round(stop, 4),
        take_profit=round(take_profit, 4),
        risk_reward=round(rr, 2),
        size=size,
        reasons=signal.reasons,
        sentiment=round(sentiment_score, 2),
        confidence=signal.confidence,
        adx=round(signal.adx, 1),
        stop_basis=basis,
        trailing_rule=trailing,
    )

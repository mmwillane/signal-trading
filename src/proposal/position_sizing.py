"""Dimensionnement de position à risque fixe.

Formule (principe "risque_fixe" du module knowledge) :

    montant_risqué = capital * risque_par_trade      (ex. 10000 * 1% = 100)
    risque_par_unité = |entrée - stop|
    quantité = montant_risqué / risque_par_unité

La quantité est bornée pour ne jamais dépasser le capital disponible
(pas de levier implicite dans les propositions).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSize:
    quantity: float          # unités/actions (fractionnable pour crypto)
    risk_amount: float       # montant en devise réellement risqué
    notional: float          # exposition = quantité * entrée
    risk_per_unit: float

    def as_dict(self) -> dict[str, float]:
        return {
            "quantity": self.quantity,
            "risk_amount": self.risk_amount,
            "notional": self.notional,
            "risk_per_unit": self.risk_per_unit,
        }


def size_position(
    *,
    capital: float,
    risk_per_trade: float,
    entry: float,
    stop: float,
    allow_fractional: bool = True,
) -> PositionSize | None:
    """Calcule la taille de position. None si les entrées sont incohérentes."""
    if capital <= 0 or not 0 < risk_per_trade <= 0.1:
        return None
    if entry <= 0 or stop <= 0 or entry == stop:
        return None

    target_risk = capital * risk_per_trade
    risk_per_unit = abs(entry - stop)
    qty = target_risk / risk_per_unit

    if not allow_fractional:
        qty = float(int(qty))  # actions : pas de fraction -> arrondi inférieur
    if qty <= 0:
        return None

    # Garde-fou anti-levier : l'exposition ne dépasse jamais le capital.
    if qty * entry > capital:
        qty = capital / entry
        if not allow_fractional:
            qty = float(int(qty))
        if qty <= 0:
            return None

    # Risque et exposition recalculés depuis la quantité FINALE : après
    # arrondi entier ou plafonnement, le risque réel diffère de la cible.
    qty = round(qty, 8)
    return PositionSize(
        quantity=qty,
        risk_amount=round(qty * risk_per_unit, 2),
        notional=round(qty * entry, 2),
        risk_per_unit=round(risk_per_unit, 6),
    )

"""Base de règles de trading — principes reconnus, reformulés.

IMPORTANT (droit d'auteur) : ce module NE contient PAS de texte recopié de
livres. Il encode des PRINCIPES largement établis et de notoriété publique
(gestion du risque, suivi de tendance, confluence, asymétrie R/R),
reformulés avec nos propres mots. Ces idées proviennent de la culture
trading générale — p. ex. couper ses pertes / laisser courir ses gains,
ne pas surdimensionner, trader dans le sens de la tendance dominante.

Pour "nourrir le bot" davantage :
- Vous POUVEZ ajouter ici vos propres notes personnelles.
- N'y collez PAS de passages de livres sous copyright.

Chaque règle est un filtre/validateur appliqué aux propositions d'ordre :
le moteur ne « croit » pas un setup qui viole ces principes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    name: str
    principle: str          # énoncé pédagogique du principe
    rationale: str          # pourquoi c'est important


# Règles de gestion du risque et de qualité de setup (de notoriété publique).
RULES: tuple[Rule, ...] = (
    Rule(
        "risque_fixe",
        "Ne jamais risquer plus qu'une petite fraction fixe du capital par trade.",
        "Limite la ruine sur une série de pertes ; rend les résultats "
        "dépendants de l'espérance, pas d'un seul trade.",
    ),
    Rule(
        "asymetrie_rr",
        "N'accepter un trade que si le gain potentiel dépasse nettement le "
        "risque (R/R >= 1.5 par défaut).",
        "Une asymétrie positive permet d'être rentable même avec un win "
        "rate inférieur à 50 %.",
    ),
    Rule(
        "sens_tendance",
        "Privilégier les entrées dans le sens de la tendance dominante "
        "(filtre par moyenne mobile longue).",
        "Trader à contre-tendance a une espérance plus faible et des "
        "stops plus souvent touchés.",
    ),
    Rule(
        "confluence",
        "Exiger la confluence d'au moins deux signaux indépendants "
        "(tendance + momentum, ou technique + sentiment) avant de proposer.",
        "Réduit les faux signaux ; un seul indicateur se trompe souvent.",
    ),
    Rule(
        "stop_base_volatilite",
        "Placer le stop en fonction de la volatilité (ATR), pas d'un montant "
        "arbitraire en devise.",
        "Le stop respecte le bruit réel de l'instrument au lieu d'être "
        "touché par des oscillations normales.",
    ),
    Rule(
        "pas_de_trade_force",
        "En l'absence de setup clair, ne rien proposer.",
        "Le sur-trading détruit le capital ; l'inaction est une position "
        "valable.",
    ),
    Rule(
        "tendance_forte_seulement",
        "N'agir que si la tendance est réellement établie (ADX >= 20).",
        "Dans un marché sans direction (range), les croisements de moyennes "
        "et le MACD génèrent surtout des faux signaux.",
    ),
    Rule(
        "stop_structurel",
        "Placer le stop au-delà d'un niveau structurel (plus bas/haut récent), "
        "borné par la volatilité, plutôt qu'à une distance ATR fixe.",
        "Le marché respecte les niveaux : un stop juste sous un support est "
        "moins souvent touché par hasard.",
    ),
    Rule(
        "confirmation_multi_temps",
        "Confirmer la direction sur une unité de temps plus fine avant d'entrer.",
        "Un alignement journalier + intraday augmente la probabilité que le "
        "mouvement soit en cours, pas déjà terminé.",
    ),
)


# Paramètres par défaut dérivés de ces principes (surchargeables).
MIN_RR = 1.7                 # asymétrie minimale exigée (relevée : qualité)
ATR_STOP_MULTIPLE = 1.5      # borne basse/haute de la distance de stop (× ATR)
ATR_TP_MULTIPLE = 2.5        # repli si pas d'objectif structurel (× ATR)
TREND_FILTER_WINDOW = 200    # SMA longue pour le sens de la tendance

# --- Filtre de force de tendance (ADX) ---
ADX_MIN = 20.0               # en dessous : marché sans tendance -> pas de setup

# --- Stop structurel ---
SWING_WINDOW = 10            # fenêtre (bougies) pour le plus bas/haut structurel
STOP_MIN_ATR = 0.8           # distance de stop min (× ATR) : évite le bruit
STOP_MAX_ATR = 3.0           # distance de stop max (× ATR) : borne le risque
STOP_ATR_BUFFER = 0.25       # marge sous le support (× ATR)
TARGET_RR = 2.0              # R/R visé pour l'objectif (>= MIN_RR)

# --- Stop suiveur (trailing) ---
TRAIL_ACTIVATE_R = 1.0       # on active le trailing une fois +1R atteint
TRAIL_ATR_MULT = 2.5         # stop suiveur à 2.5 × ATR du plus haut/bas atteint

# --- Score de confiance ---
CONFIDENCE_MIN = 55          # score minimal (0-100) pour proposer un setup


def rules_summary() -> str:
    """Texte lisible des principes appliqués (pour le README / affichage)."""
    return "\n".join(f"- {r.name}: {r.principle}" for r in RULES)

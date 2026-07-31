"""Couche IA CONSULTATIVE (analyste), optionnelle.

Cette couche NE prend AUCUNE décision automatisée : elle lit un instantané
technique déjà calculé (déterministe) + des titres de news, et rend une
appréciation qualitative (conviction, facteurs, risques, raisonnement).

Invariants (voir src/ai/analyst.py) :
- Ne calcule JAMAIS la taille de position ni les niveaux (stop/TP) — cela
  reste 100 % Python déterministe. L'IA ne fait qu'expliquer/pondérer.
- Ne « prédit » pas le marché ; aucune garantie de résultat.
- Traite les news comme des données NON FIABLES (anti-injection).
- Désactivée proprement si aucune clé ANTHROPIC_API_KEY n'est configurée.
"""

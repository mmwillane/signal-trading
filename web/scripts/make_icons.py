"""Génère les icônes PWA (fond OLED sombre + motif signal haussier émeraude).

Usage : python scripts/make_icons.py
Sort : public/icon-192.png, icon-512.png, apple-touch-icon.png
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(__file__), "..", "public")
os.makedirs(OUT, exist_ok=True)

BG = (7, 7, 9)          # #070709 OLED
PANEL = (12, 13, 16)
EMERALD = (52, 211, 153)
EMERALD_DIM = (16, 122, 89)
ROSE = (244, 63, 94)


def rounded(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(size * 0.22)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG)

    # Lueur radiale émeraude en haut à droite (mesh gradient simplifié).
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = int(size * 0.72), int(size * 0.28)
    for i in range(int(size * 0.5), 0, -2):
        a = int(70 * (1 - i / (size * 0.5)))
        gd.ellipse([cx - i, cy - i, cx + i, cy + i], fill=(52, 211, 153, max(a, 0)))
    img = Image.alpha_composite(img, glow)

    d = ImageDraw.Draw(img)
    # Bougies : deux rouges puis trois vertes montantes (récit haussier).
    unit = size / 22
    def candle(col, cx_u, top_u, bot_u, wick_top_u, wick_bot_u, w=1.7):
        x = cx_u * unit
        d.line([(x, wick_top_u * unit), (x, wick_bot_u * unit)], fill=col, width=max(int(unit * 0.28), 2))
        d.rounded_rectangle(
            [x - w * unit / 2, top_u * unit, x + w * unit / 2, bot_u * unit],
            radius=max(int(unit * 0.25), 1), fill=col,
        )

    candle(ROSE, 5, 12, 15, 11, 16)
    candle(ROSE, 8, 11, 13.5, 10, 15)
    candle(EMERALD_DIM, 11, 9, 12, 8, 13)
    candle(EMERALD, 14, 6.5, 10, 5.5, 11)
    candle(EMERALD, 17, 4.5, 8, 3.5, 9)

    # Ligne de tendance ascendante.
    d.line([(4 * unit, 14 * unit), (17.5 * unit, 5.5 * unit)],
           fill=(52, 211, 153, 255), width=max(int(unit * 0.22), 2), joint="curve")
    return img


for s, name in [(512, "icon-512.png"), (192, "icon-192.png"), (180, "apple-touch-icon.png")]:
    rounded(s).save(os.path.join(OUT, name))
    print("écrit", name)

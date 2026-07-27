"""Bootstrap console : force UTF-8 sur stdout/stderr.

Sous Windows, la console par défaut est souvent en cp1252 et lève une
UnicodeEncodeError sur les accents ou les caractères de cadre. On
reconfigure les flux en UTF-8 (avec repli 'replace') pour ne jamais
planter à l'affichage, tout en gardant une mise en forme lisible.
"""

from __future__ import annotations

import sys


def enable_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

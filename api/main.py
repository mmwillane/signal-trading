"""API HTTP de l'assistant de trading — analyse LECTURE SEULE.

Expose la logique de src/ en JSON pour le frontend web/mobile.

INVARIANT BROKER : aucun endpoint n'exécute, ne modifie ni n'annule
d'ordre chez un broker. Les seules écritures (POST/PATCH/DELETE) concernent
le JOURNAL DE TRADES LOCAL : des notes de l'utilisateur sur ses propres
trades manuels, stockées dans un fichier local. Elles ne touchent jamais
un compte broker.

Lancement (dev) :
    uvicorn api.main:app --reload --port 8010
"""

from __future__ import annotations

from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles

from src.journal.store import JournalError
from src.security.console import enable_utf8
from src.security.env import ConfigError
from src.security.safe_logging import get_logger

from . import services

enable_utf8()
log = get_logger("api")

app = FastAPI(
    title="Assistant de trading — API",
    version="2.0.0",
    description="Aide à la décision. N'exécute jamais d'ordre chez un broker.",
)

# En dev, le frontend Vite tourne sur un autre port : on autorise le CORS
# local. Les écritures ne concernent que le journal local (pas de broker).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "mode": "read-only", "executes_orders": False}


@app.get("/api/settings")
def get_settings() -> dict:
    try:
        return services.settings_dict()
    except ConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/dashboard")
def get_dashboard(
    news: bool = Query(default=True),
    capital: float | None = Query(default=None),
    risk: float | None = Query(default=None),
    fractional: bool = Query(default=False),
    more_signals: bool = Query(default=False),
    currency: str | None = Query(default=None),
) -> dict:
    try:
        return services.dashboard(
            use_news=news, capital=capital, risk=risk,
            fractional=fractional, more_signals=more_signals, currency=currency,
        )
    except ConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/instrument/{symbol}")
def get_instrument(
    symbol: str,
    news: bool = Query(default=True),
    timeframe: str = Query(default="daily"),
    capital: float | None = Query(default=None),
    risk: float | None = Query(default=None),
    fractional: bool = Query(default=False),
    more_signals: bool = Query(default=False),
    currency: str | None = Query(default=None),
) -> dict:
    tf = timeframe if timeframe in ("daily", "intraday") else "daily"
    data = services.instrument_detail(
        symbol.upper(), use_news=news, timeframe=tf, capital=capital, risk=risk,
        fractional=fractional, more_signals=more_signals, currency=currency,
    )
    if data.get("status") == "insufficient_data":
        raise HTTPException(status_code=404, detail="Données insuffisantes pour ce symbole")
    return data


@app.get("/api/quotes")
def get_quotes(symbols: str = Query(...)) -> dict:
    """Cotations live légères (rafraîchissement rapide). symbols=AAPL,MSFT,..."""
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()][:25]
    return services.quotes(syms)


@app.get("/api/news")
def get_news() -> dict:
    return services.news_feed()


@app.get("/api/backtest/{symbol}")
def get_backtest(
    symbol: str,
    period: str = Query(default="2y"),
    trailing: bool = Query(default=True),
) -> dict:
    data = services.backtest(symbol.upper(), period=period, trailing=trailing)
    if data.get("status") == "insufficient_data":
        raise HTTPException(status_code=404, detail="Données insuffisantes pour le backtest")
    return data


@app.get("/api/portfolio")
def get_portfolio() -> dict:
    return services.portfolio()


# --- Journal de trades (écritures LOCALES ; jamais un broker) -------------
@app.get("/api/journal")
def get_journal() -> dict:
    return services.journal_view()


@app.post("/api/journal")
def post_journal(payload: dict = Body(...)) -> dict:
    try:
        return services.journal_add(payload)
    except JournalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/journal/{trade_id}/close")
def patch_journal_close(trade_id: str, payload: dict = Body(...)) -> dict:
    exit_price = payload.get("exit_price")
    if exit_price is None:
        raise HTTPException(status_code=400, detail="Prix de sortie requis.")
    try:
        return services.journal_close(trade_id, exit_price)
    except JournalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/journal/{trade_id}")
def delete_journal(trade_id: str) -> dict:
    ok = services.journal_delete(trade_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Trade introuvable.")
    return {"deleted": True}


# --- Service du frontend (mode partage : une seule URL) -------------------
# Si le frontend a été buildé (web/dist), on le sert directement ici. Ainsi
# toute l'app est disponible sur un seul port/une seule URL, facile à
# partager. En dev (pas de dist), on ne monte rien : Vite sert le front.
class _SPAStaticFiles(StaticFiles):
    """Sert les fichiers statiques avec repli SPA sur index.html.

    Nécessaire pour que les routes côté client (/journal, /instrument/AAPL)
    fonctionnent au rechargement direct.
    """

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


_DIST = Path(__file__).resolve().parents[1] / "web" / "dist"
if _DIST.is_dir():
    app.mount("/", _SPAStaticFiles(directory=str(_DIST), html=True), name="spa")
    log.info("Frontend servi depuis %s (mode partage, une seule URL).", _DIST)
else:
    log.info("Pas de web/dist : mode dev (Vite sert le frontend séparément).")

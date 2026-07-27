"""Lance le backtest de la logique de setup sur chaque instrument.

Usage :
    python run_backtest.py                 # watchlist du .env, 2 ans
    python run_backtest.py AAPL MSFT       # symboles explicites
    python run_backtest.py --period 5y
"""

from __future__ import annotations

import argparse

from src.security.console import enable_utf8

enable_utf8()  # avant tout affichage (consoles Windows cp1252)

from src.backtest.engine import run_backtest
from src.data.market_data import get_history
from src.knowledge import trading_rules as tr
from src.security.env import ConfigError, load_settings
from src.security.safe_logging import get_logger

log = get_logger("backtest")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest (données historiques)")
    parser.add_argument("symbols", nargs="*", help="Symboles (défaut : watchlist .env)")
    parser.add_argument("--period", default="2y", help="Période yfinance (défaut 2y)")
    args = parser.parse_args()

    symbols = [s.upper() for s in args.symbols]
    if not symbols:
        try:
            symbols = list(load_settings().watchlist)
        except ConfigError as exc:
            log.error("Config invalide :\n%s", exc)
            return 1

    print("Backtest — rappel : le passé ne préjuge pas du futur.\n")
    for symbol in symbols:
        df = get_history(symbol, period=args.period, interval="1d")
        if df is None or len(df) < tr.TREND_FILTER_WINDOW + 10:
            print(f"[{symbol}] données insuffisantes.\n")
            continue
        stats, _trades = run_backtest(df)
        print(f"### {symbol}")
        print(stats.render(), "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

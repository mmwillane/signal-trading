"""Backtest de la logique de setup sur données historiques.

Méthodo (simple et honnête, pas de sur-optimisation) :
- On parcourt l'historique bougie par bougie.
- Sur un signal, on ouvre un trade virtuel avec le MÊME calcul de stop/TP
  que les propositions live (via analyzer + trading_rules).
- On simule la sortie sur les bougies suivantes : stop touché, TP touché,
  ou clôture forcée en fin de données.
- Hypothèse prudente : si dans la même bougie High et Low touchent TP et
  stop, on suppose le STOP touché d'abord (pessimiste = plus crédible).
- Pas de sentiment dans le backtest (les news historiques ne sont pas
  rejouables proprement) : on teste la robustesse du signal technique seul.

⚠ Un backtest décrit le PASSÉ. Il ne garantit rien sur le futur.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..analysis.analyzer import compute_features, evaluate_row
from ..knowledge import trading_rules as tr
from ..proposal.order_proposal import compute_stop


@dataclass(frozen=True)
class Trade:
    direction: str
    entry: float
    stop: float
    take_profit: float
    exit_price: float
    r_multiple: float        # gain/perte en multiples du risque initial
    outcome: str             # "tp" | "stop" | "trail" | "eod"


@dataclass(frozen=True)
class BacktestStats:
    n_trades: int
    win_rate: float
    profit_factor: float
    avg_rr: float
    max_drawdown_r: float    # drawdown max exprimé en R (cumul)
    total_r: float

    def render(self) -> str:
        if self.n_trades == 0:
            return "Backtest : aucun trade déclenché sur la période."
        return (
            f"Backtest — {self.n_trades} trades\n"
            f"  Win rate       : {self.win_rate:.1%}\n"
            f"  Profit factor  : {self.profit_factor:.2f}\n"
            f"  R/R moyen      : {self.avg_rr:.2f}\n"
            f"  Drawdown max   : {self.max_drawdown_r:.2f} R\n"
            f"  Résultat total : {self.total_r:+.2f} R"
        )


def run_backtest(df: pd.DataFrame, *, use_trailing: bool = True) -> tuple[BacktestStats, list[Trade]]:
    """Exécute le backtest et renvoie stats + liste de trades.

    Utilise EXACTEMENT le calcul de stop/objectif des propositions live
    (compute_stop structurel + R/R cible), et simule un stop suiveur optionnel.
    """
    feat = compute_features(df)
    trades: list[Trade] = []
    i = 0
    n = len(feat)

    while i < n - 1:
        signal = evaluate_row(feat.iloc[i], sentiment_score=0.0)
        if not signal.has_setup or signal.atr <= 0:
            i += 1
            continue

        entry = signal.close
        stop, stop_dist, _basis = compute_stop(signal)
        if stop_dist <= 0:
            i += 1
            continue
        rr = max(tr.TARGET_RR, tr.MIN_RR)
        tp_dist = rr * stop_dist
        long = signal.direction == "buy"
        tp = entry + tp_dist if long else entry - tp_dist

        trade, next_i = _simulate_exit(
            feat, i, entry, stop, tp, stop_dist, signal.atr, long, use_trailing
        )
        trades.append(trade)
        # On saute jusqu'à la sortie : pas de trades chevauchants.
        i = next_i + 1

    return _aggregate(trades), trades


def _simulate_exit(
    feat: pd.DataFrame,
    start: int,
    entry: float,
    stop: float,
    tp: float,
    risk: float,
    atr: float,
    long: bool,
    use_trailing: bool,
) -> tuple[Trade, int]:
    direction = "buy" if long else "sell"
    cur_stop = stop
    trailed = False
    extremum = entry  # plus haut (long) ou plus bas (short) atteint

    for j in range(start + 1, len(feat)):
        high = float(feat["High"].iloc[j])
        low = float(feat["Low"].iloc[j])

        # 1) Sorties évaluées AVANT la mise à jour du trailing de cette bougie
        #    (pessimiste : on n'utilise pas le high de la bougie pour trailer
        #     puis la même bougie pour se faire sortir plus haut).
        hit_stop = low <= cur_stop if long else high >= cur_stop
        hit_tp = high >= tp if long else low <= tp

        if hit_stop:  # stop prioritaire
            outcome = "trail" if trailed else "stop"
            return _make_trade(direction, entry, cur_stop, tp, cur_stop, risk, long, outcome), j
        if hit_tp:
            return _make_trade(direction, entry, cur_stop, tp, tp, risk, long, "tp"), j

        # 2) Mise à jour du stop suiveur pour les bougies suivantes.
        if use_trailing:
            extremum = max(extremum, high) if long else min(extremum, low)
            in_profit = (extremum - entry) >= risk if long else (entry - extremum) >= risk
            if in_profit:
                candidate = (
                    extremum - tr.TRAIL_ATR_MULT * atr
                    if long
                    else extremum + tr.TRAIL_ATR_MULT * atr
                )
                new_stop = max(cur_stop, candidate) if long else min(cur_stop, candidate)
                if new_stop != cur_stop:
                    cur_stop = new_stop
                    trailed = True

    # Fin des données : clôture au dernier prix connu.
    last = float(feat["Close"].iloc[-1])
    return _make_trade(direction, entry, cur_stop, tp, last, risk, long, "eod"), len(feat) - 1


def _make_trade(direction, entry, stop, tp, exit_price, risk, long, outcome) -> Trade:
    pnl = (exit_price - entry) if long else (entry - exit_price)
    r_multiple = pnl / risk if risk else 0.0
    return Trade(
        direction=direction,
        entry=round(entry, 4),
        stop=round(stop, 4),
        take_profit=round(tp, 4),
        exit_price=round(exit_price, 4),
        r_multiple=round(r_multiple, 3),
        outcome=outcome,
    )


def _aggregate(trades: list[Trade]) -> BacktestStats:
    if not trades:
        return BacktestStats(0, 0.0, 0.0, 0.0, 0.0, 0.0)

    r_values = [t.r_multiple for t in trades]
    wins = [r for r in r_values if r > 0]
    losses = [r for r in r_values if r < 0]

    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")

    # Drawdown max sur la courbe cumulée de R.
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in r_values:
        cumulative += r
        peak = max(peak, cumulative)
        max_dd = min(max_dd, cumulative - peak)

    return BacktestStats(
        n_trades=len(trades),
        win_rate=len(wins) / len(trades),
        profit_factor=round(profit_factor, 2) if profit_factor != float("inf") else float("inf"),
        avg_rr=round(sum(r_values) / len(r_values), 3),
        max_drawdown_r=round(max_dd, 2),
        total_r=round(sum(r_values), 2),
    )

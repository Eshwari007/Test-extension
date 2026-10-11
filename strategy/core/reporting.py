"""Metrics reported for every run (plan: "Metrics reported for every run").

Net CAGR, max drawdown, Calmar, Sharpe, Sortino, profit factor, expectancy in
R, win rate, average win/loss, trade count, exposure %, worst day, longest
time to recover, fees as % of gross profit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

BARS_PER_YEAR = {"1m": 525_600, "15m": 35_040, "1h": 8_760, "1d": 365}


def max_drawdown(equity: pd.Series) -> tuple[float, int]:
    """Return (max drawdown fraction, longest bars-to-recover)."""
    if equity.empty:
        return 0.0, 0
    peak = equity.cummax()
    dd = 1 - equity / peak
    under = (dd > 0).astype(int)
    longest = cur = 0
    for u in under:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    return float(dd.max()), int(longest)


def cagr(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    years = (equity.index[-1] - equity.index[0]).total_seconds() / (365.25 * 86400)
    if years <= 0:
        return 0.0
    ratio = equity.iloc[-1] / equity.iloc[0]
    if ratio <= 0:
        return -1.0
    return float(ratio ** (1 / years) - 1)


def sharpe(returns: pd.Series, periods_per_year: int) -> float:
    if len(returns) < 2 or returns.std(ddof=1) == 0:
        return 0.0
    return float(returns.mean() / returns.std(ddof=1) * np.sqrt(periods_per_year))


def sortino(returns: pd.Series, periods_per_year: int) -> float:
    downside = returns[returns < 0]
    if len(returns) < 2 or len(downside) == 0:
        return 0.0
    dd = np.sqrt((downside**2).mean())
    if dd == 0:
        return 0.0
    return float(returns.mean() / dd * np.sqrt(periods_per_year))


def daily_equity(equity: pd.Series) -> pd.Series:
    return equity.resample("1D").last().dropna()


def compute_metrics(
    equity: pd.Series,
    trades: pd.DataFrame,
    timeframe: str = "1d",
    exposure_series: pd.Series | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if equity.empty:
        return {"error": "empty equity"}
    daily = daily_equity(equity)
    rets = daily.pct_change().dropna()
    mdd, recover = max_drawdown(daily)
    out["net_return"] = float(equity.iloc[-1] / equity.iloc[0] - 1)
    out["cagr"] = cagr(daily)
    out["max_drawdown"] = mdd
    out["calmar"] = out["cagr"] / mdd if mdd > 0 else (np.inf if out["cagr"] > 0 else 0.0)
    out["sharpe"] = sharpe(rets, 365)
    out["sortino"] = sortino(rets, 365)
    out["worst_day"] = float(rets.min()) if len(rets) else 0.0
    out["longest_recovery_days"] = recover
    out["exposure_pct"] = float(exposure_series.mean()) if exposure_series is not None and len(exposure_series) else 0.0

    n = len(trades)
    out["trade_count"] = int(n)
    if n:
        pnl = trades["net_pnl"]
        wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
        gross_profit = float(wins.sum())
        gross_loss = float(-losses.sum())
        out["win_rate"] = float(len(wins) / n)
        out["avg_win"] = float(wins.mean()) if len(wins) else 0.0
        out["avg_loss"] = float(losses.mean()) if len(losses) else 0.0
        out["profit_factor"] = gross_profit / gross_loss if gross_loss > 0 else (np.inf if gross_profit > 0 else 0.0)
        out["expectancy_r"] = float(trades["r_multiple"].mean())
        out["fees_total"] = float(trades["fees"].sum())
        out["fees_pct_gross_profit"] = float(trades["fees"].sum() / gross_profit) if gross_profit > 0 else np.inf
        by_coin = trades.groupby("symbol")["net_pnl"].sum()
        total = float(pnl.sum())
        out["max_coin_profit_share"] = float(by_coin.max() / total) if total > 0 else np.nan
    else:
        out.update(win_rate=0.0, avg_win=0.0, avg_loss=0.0, profit_factor=0.0, expectancy_r=0.0,
                   fees_total=0.0, fees_pct_gross_profit=0.0, max_coin_profit_share=np.nan)
    return out


def format_metrics(m: dict[str, Any]) -> str:
    keys = [
        ("net_return", "{:+.2%}"), ("cagr", "{:+.2%}"), ("max_drawdown", "{:.2%}"), ("calmar", "{:.2f}"),
        ("sharpe", "{:.2f}"), ("sortino", "{:.2f}"), ("profit_factor", "{:.2f}"), ("expectancy_r", "{:+.3f}"),
        ("win_rate", "{:.1%}"), ("avg_win", "{:,.2f}"), ("avg_loss", "{:,.2f}"), ("trade_count", "{}"),
        ("exposure_pct", "{:.1%}"), ("worst_day", "{:+.2%}"), ("longest_recovery_days", "{}"),
        ("fees_pct_gross_profit", "{:.1%}"), ("max_coin_profit_share", "{:.1%}"),
    ]
    lines = []
    for k, fmt in keys:
        if k in m:
            v = m[k]
            try:
                lines.append(f"  {k:<24} {fmt.format(v)}")
            except (ValueError, TypeError):
                lines.append(f"  {k:<24} {v}")
    return "\n".join(lines)


class RunLog:
    """Append-only JSONL log of every configuration ever run (data-snooping count)."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, entry: dict[str, Any]) -> None:
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, default=_json_default) + "\n")

    def count(self) -> int:
        if not self.path.exists():
            return 0
        with open(self.path, encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]


def _json_default(o: Any) -> Any:
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    if isinstance(o, float) and (np.isnan(o) or np.isinf(o)):
        return None
    return str(o)

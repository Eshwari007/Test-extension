"""Validation protocol (plan: "Validation protocol" and "Strategy selection scorecard").

Seven tests, run in Phase 4 on the frozen spec:
  1. hold-out (one run; the caller does it with run_backtest)
  2. walk-forward        -> walk_forward()
  3. parameter sensitivity -> parameter_sensitivity()
  4. cost stress         -> run_backtest(stress=True, taker_everywhere=True)
  5. Monte Carlo         -> monte_carlo()
  6. random-entry benchmark -> random_entry_benchmark()
  7. regime/coin breakdown -> breakdown()
plus the deflated Sharpe ratio, the Kelly estimate for the tier rule, the
hard gates and the weighted ranking.

Every function is deterministic for a given seed and logs it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import NormalDist
from typing import Any, Callable

import numpy as np
import pandas as pd

from .backtest import BacktestResult, run_backtest
from .config import RiskTier, Spec
from .reporting import compute_metrics
from .signals import RandomEntry, Strategy

RunFn = Callable[..., BacktestResult]
_NORM = NormalDist()


def norm_cdf(x: float) -> float:
    return _NORM.cdf(float(x))


def norm_ppf(p: float) -> float:
    return _NORM.inv_cdf(float(np.clip(p, 1e-12, 1 - 1e-12)))


# ---------------------------------------------------------------------------
# 2. Walk-forward
# ---------------------------------------------------------------------------
@dataclass
class WalkForwardWindow:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    chosen_variant: str | None
    train_calmar: float
    test_net_pnl: float
    test_trades: int


@dataclass
class WalkForwardResult:
    windows: list[WalkForwardWindow]

    @property
    def positive_fraction(self) -> float:
        if not self.windows:
            return 0.0
        return sum(1 for w in self.windows if w.test_net_pnl > 0) / len(self.windows)

    @property
    def max_window_profit_share(self) -> float:
        total = sum(w.test_net_pnl for w in self.windows)
        if total <= 0:
            return np.nan
        return max(w.test_net_pnl for w in self.windows) / total

    def passed(self, min_positive: float = 0.60, max_share: float = 0.40) -> bool:
        share = self.max_window_profit_share
        return self.positive_fraction >= min_positive and (np.isnan(share) or share <= max_share)


def walk_forward(
    run: Callable[[str | None, pd.Timestamp, pd.Timestamp], BacktestResult],
    variants: list[str | None],
    start: pd.Timestamp,
    end: pd.Timestamp,
    train_months: int = 12,
    test_months: int = 3,
) -> WalkForwardResult:
    """Rolling train/test. In each train window only pre-registered `variants` may be chosen."""
    windows: list[WalkForwardWindow] = []
    cur = pd.Timestamp(start)
    while True:
        train_end = cur + pd.DateOffset(months=train_months)
        test_end = train_end + pd.DateOffset(months=test_months)
        if test_end > end:
            break
        best, best_calmar = None, -np.inf
        for v in variants:
            res = run(v, cur, train_end)
            m = res.metrics()
            c = m.get("calmar", -np.inf)
            if np.isinf(c):
                c = 1e9 if c > 0 else -1e9
            if c > best_calmar:
                best, best_calmar = v, c
        test = run(best, train_end, test_end)
        windows.append(WalkForwardWindow(cur, train_end, train_end, test_end, best, best_calmar,
                                         float(test.trades["net_pnl"].sum()) if len(test.trades) else 0.0,
                                         len(test.trades)))
        cur = cur + pd.DateOffset(months=test_months)
    return WalkForwardResult(windows)


# ---------------------------------------------------------------------------
# 3. Parameter sensitivity
# ---------------------------------------------------------------------------
@dataclass
class SensitivityResult:
    baseline_calmar: float
    grid: pd.DataFrame  # columns: param, value, calmar, net_return, max_drawdown

    @property
    def worst_ratio(self) -> float:
        if self.baseline_calmar <= 0 or self.grid.empty:
            return 0.0
        return float(self.grid["calmar"].min() / self.baseline_calmar)

    def passed(self, floor: float = 0.5) -> bool:
        return self.worst_ratio >= floor


def parameter_sensitivity(
    strategy: Strategy,
    run: Callable[[Strategy], BacktestResult],
    shifts: tuple[float, ...] = (-0.25, 0.25),
) -> SensitivityResult:
    """One-at-a-time +/-25% shifts of every free parameter."""
    base = run(strategy).metrics()
    rows = []
    for name, value in strategy.parameter_grid().items():
        for s in shifts:
            new = value * (1 + s)
            if isinstance(value, int):
                new = max(1, int(round(new)))
                if new == value:
                    continue
            m = run(strategy.with_parameters({name: new})).metrics()
            rows.append({"param": name, "value": new, "calmar": _finite(m["calmar"]),
                         "net_return": m["net_return"], "max_drawdown": m["max_drawdown"]})
    return SensitivityResult(_finite(base["calmar"]), pd.DataFrame(rows))


def _finite(x: float) -> float:
    if np.isinf(x):
        return 1e9 if x > 0 else -1e9
    return float(x)


# ---------------------------------------------------------------------------
# 5. Monte Carlo resampling
# ---------------------------------------------------------------------------
@dataclass
class MonteCarloResult:
    n_runs: int
    seed: int
    dd_p95: float
    dd_p50: float
    terminal_p05: float
    terminal_p50: float
    terminal_p95: float
    paths_p05: np.ndarray = field(repr=False, default_factory=lambda: np.array([]))
    paths_p95: np.ndarray = field(repr=False, default_factory=lambda: np.array([]))

    def passed(self, tier: RiskTier) -> bool:
        return self.dd_p95 <= tier.max_drawdown


def monte_carlo(trade_returns: np.ndarray | pd.Series, n_runs: int = 5000, seed: int = 0) -> MonteCarloResult:
    """Bootstrap the trade sequence; each trade's return is applied to the whole equity
    scaled by the fraction of equity that trade actually used (`trade_returns` should be
    the per-trade return on EQUITY, i.e. net_pnl / equity_at_entry).
    """
    r = np.asarray(trade_returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return MonteCarloResult(n_runs, seed, 0.0, 0.0, 1.0, 1.0, 1.0)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(r), size=(n_runs, len(r)))
    paths = np.cumprod(1 + r[idx], axis=1)
    peaks = np.maximum.accumulate(np.concatenate([np.ones((n_runs, 1)), paths], axis=1), axis=1)[:, 1:]
    dd = (1 - paths / peaks).max(axis=1)
    terminal = paths[:, -1]
    return MonteCarloResult(
        n_runs, seed,
        dd_p95=float(np.percentile(dd, 95)), dd_p50=float(np.percentile(dd, 50)),
        terminal_p05=float(np.percentile(terminal, 5)), terminal_p50=float(np.percentile(terminal, 50)),
        terminal_p95=float(np.percentile(terminal, 95)),
        paths_p05=np.percentile(paths, 5, axis=0), paths_p95=np.percentile(paths, 95, axis=0),
    )


def trade_returns_on_equity(result: BacktestResult) -> np.ndarray:
    """net_pnl / equity at entry, for Monte Carlo."""
    if result.trades.empty:
        return np.array([])
    eq = result.equity
    out = []
    for _, tr in result.trades.iterrows():
        i = eq.index.searchsorted(tr["entry_time"], side="right") - 1
        e = float(eq.iloc[max(i, 0)])
        out.append(tr["net_pnl"] / e if e > 0 else 0.0)
    return np.asarray(out)


# ---------------------------------------------------------------------------
# 6. Random-entry benchmark (K11)
# ---------------------------------------------------------------------------
@dataclass
class RandomEntryResult:
    real_value: float
    random_values: np.ndarray
    metric: str
    seed: int

    @property
    def percentile(self) -> float:
        if len(self.random_values) == 0:
            return np.nan
        return float((self.random_values < self.real_value).mean())

    def passed(self, threshold: float = 0.95) -> bool:
        return self.percentile > threshold


def random_entry_benchmark(
    spec: Spec,
    strategy: Strategy,
    real: BacktestResult,
    run_kwargs: dict[str, Any],
    n_runs: int = 1000,
    seed: int = 0,
    metric: str = "net_return",
    calibration_runs: int = 5,
) -> RandomEntryResult:
    """Random entries with identical exits, sizing, regime filter and trade count.

    The entry probability is calibrated so the random runs produce about the
    same number of trades as the real run.
    """
    target = max(len(real.trades), 1)
    prob = 0.05
    for _ in range(calibration_runs):
        counts = []
        for k in range(3):
            res = run_backtest(spec, RandomEntry(strategy, prob, seed * 1000 + k), **run_kwargs)
            counts.append(len(res.trades))
        avg = max(np.mean(counts), 1e-9)
        prob = float(np.clip(prob * target / avg, 1e-5, 1.0))
    values = []
    for k in range(n_runs):
        res = run_backtest(spec, RandomEntry(strategy, prob, seed * 100_000 + 7 + k), **run_kwargs)
        values.append(res.metrics()[metric])
    return RandomEntryResult(real.metrics()[metric], np.asarray(values, dtype=float), metric, seed)


# ---------------------------------------------------------------------------
# 7. Regime and coin breakdown
# ---------------------------------------------------------------------------
def breakdown(result: BacktestResult, btc_daily: pd.DataFrame, coin_tier: Callable[[str], str], sma: int = 200) -> dict[str, pd.Series]:
    """Net P&L split by BTC regime (bull/bear/chop), by coin tier and by coin."""
    if result.trades.empty:
        return {}
    close = btc_daily["close"]
    ma = close.rolling(sma, min_periods=sma).mean()
    ret60 = close / close.shift(60) - 1
    regime = pd.Series("chop", index=close.index)
    regime[(close > ma) & (ret60 > 0.10)] = "bull"
    regime[(close < ma) & (ret60 < -0.10)] = "bear"
    tr = result.trades.copy()
    tr["regime"] = [regime.asof(t) if t >= regime.index[0] else "chop" for t in tr["entry_time"]]
    tr["tier"] = tr["symbol"].map(coin_tier)
    return {
        "by_regime": tr.groupby("regime")["net_pnl"].sum(),
        "by_tier": tr.groupby("tier")["net_pnl"].sum(),
        "by_coin": tr.groupby("symbol")["net_pnl"].sum().sort_values(ascending=False),
    }


# ---------------------------------------------------------------------------
# Deflated Sharpe ratio (Bailey & Lopez de Prado, 2014)
# ---------------------------------------------------------------------------
def deflated_sharpe(sharpe_annual: float, n_trials: int, n_obs: int, skew: float, kurt: float,
                    periods_per_year: int = 365, sharpe_var: float | None = None) -> float:
    """Probability that the observed Sharpe exceeds the max expected from `n_trials` random trials."""
    if n_obs < 3 or n_trials < 1:
        return 0.0
    sr = sharpe_annual / np.sqrt(periods_per_year)  # per-period
    if sharpe_var is None:
        sharpe_var = (1 - skew * sr + (kurt - 1) / 4 * sr**2) / max(n_obs - 1, 1)
    sd = np.sqrt(max(sharpe_var, 1e-12))
    euler = 0.5772156649
    if n_trials == 1:
        sr0 = 0.0
    else:
        sr0 = sd * ((1 - euler) * norm_ppf(1 - 1 / n_trials) + euler * norm_ppf(1 - 1 / (n_trials * np.e)))
    z = (sr - sr0) * np.sqrt(n_obs - 1) / np.sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr**2, 1e-12))
    return float(norm_cdf(z))


def sharpe_inputs(equity: pd.Series) -> dict[str, float]:
    daily = equity.resample("1D").last().dropna().pct_change().dropna()
    if len(daily) < 3:
        return {"n_obs": len(daily), "skew": 0.0, "kurt": 3.0}
    m = daily.mean()
    s = daily.std(ddof=1)
    z = (daily - m) / s if s > 0 else daily * 0
    return {"n_obs": len(daily), "skew": float((z**3).mean()), "kurt": float((z**4).mean())}


# ---------------------------------------------------------------------------
# Kelly estimate for the tier rule
# ---------------------------------------------------------------------------
def kelly_fraction(trade_returns: np.ndarray | pd.Series) -> float:
    """Growth-optimal fraction of equity per trade ~ mean / variance of trade returns."""
    r = np.asarray(trade_returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2 or r.var(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.var(ddof=1))


# ---------------------------------------------------------------------------
# Hard gates and ranking
# ---------------------------------------------------------------------------
@dataclass
class GateInputs:
    candidate: str
    tier: RiskTier
    oos_metrics: dict[str, Any]
    stress_metrics: dict[str, Any]
    mc: MonteCarloResult
    random_entry: RandomEntryResult | None
    walk_forward: WalkForwardResult
    min_trades: int


def hard_gates(g: GateInputs) -> dict[str, bool]:
    m = g.oos_metrics
    share = m.get("max_coin_profit_share", np.nan)
    wf_share = g.walk_forward.max_window_profit_share
    return {
        "net_return_positive": m["net_return"] > 0,
        "max_dd_within_2_3_tier": m["max_drawdown"] <= (2 / 3) * g.tier.max_drawdown,
        "mc_p95_dd_within_tier": g.mc.dd_p95 <= g.tier.max_drawdown,
        "beats_random_entry": g.random_entry.passed() if g.random_entry is not None else False,
        "walk_forward_60pct": g.walk_forward.positive_fraction >= 0.60,
        "survives_double_cost": g.stress_metrics["net_return"] > 0,
        "min_oos_trades": m["trade_count"] >= g.min_trades,
        "profit_concentration": (np.isnan(share) or share <= 0.30) and (np.isnan(wf_share) or wf_share <= 0.40),
    }


RANK_WEIGHTS = {
    "calmar": 0.35,
    "walk_forward_consistency": 0.20,
    "sortino": 0.15,
    "parameter_robustness": 0.15,
    "fees_pct_gross_profit": 0.10,   # lower is better
    "simplicity": 0.05,              # fewer free parameters is better
}
LOWER_IS_BETTER = {"fees_pct_gross_profit", "simplicity"}


def rank_survivors(scores: pd.DataFrame) -> pd.Series:
    """Rank 1-N on each metric across survivors at the same tier, then weight.

    `scores` has one row per survivor and the columns in RANK_WEIGHTS.
    Returns the weighted score per survivor (lower is better).
    """
    total = pd.Series(0.0, index=scores.index)
    for col, w in RANK_WEIGHTS.items():
        asc = col in LOWER_IS_BETTER
        total += scores[col].rank(ascending=asc, method="min") * w
    return total.sort_values()

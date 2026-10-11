"""Phase 3 — in-sample research on the training period only.

Runs every pre-registered candidate/variant at every risk tier, plus the cost-stress case and the
benchmarks, and writes strategy/runs/phase3/. Nothing is tuned; only pre-registered variants run.

    python -m strategy.phase3_sweep [--start 2021-01-01] [--end 2023-12-31] [--candidates C2,C3]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from . import cli
from .core.backtest import benchmark_buy_and_hold, run_backtest
from .core.config import load_spec
from .core.reporting import RunLog, compute_metrics
from .core.signals import make_strategy

OUT = Path("strategy/runs/phase3")
METRIC_KEYS = ("net_return", "cagr", "max_drawdown", "calmar", "sharpe", "sortino", "profit_factor", "expectancy_r",
               "win_rate", "trade_count", "exposure_pct", "worst_day", "fees_pct_gross_profit", "max_coin_profit_share", "killed")


def _ns(cand, variant, tier, start, end):
    return argparse.Namespace(candidate=cand, variant=variant, tier=tier, data="strategy/data/bars", ref="strategy/data/ref",
                              eligibility="strategy/data", start=start, end=end, cash=10_000.0, stress=False, synthetic=False,
                              n_synthetic=0, benchmarks=False, no_verify=False, out=None, seed=0, mc_runs=0, random_runs=0)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2021-01-01")
    p.add_argument("--end", default="2023-12-31")
    p.add_argument("--candidates", default="C2,C3")
    p.add_argument("--tiers", default="T1,T2,T3,T4")
    a = p.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    plan = {"C1": [None], "C2": ["V1", "V2", "V3"], "C3": [None]}
    rows, cache = [], {}
    for cand in a.candidates.split(","):
        spec = load_spec(cand)
        cache[cand] = cli._load_bars(_ns(cand, None, "T2", a.start, a.end), spec)
        bars, btc_daily, btc_signal = cache[cand]
        elig = cli._load_eligibility(_ns(cand, None, "T2", a.start, a.end), spec)
        for v in plan[cand]:
            for tier in a.tiers.split(","):
                for stress in (False, True):
                    r = run_backtest(spec, make_strategy(spec.candidate, v), bars, btc_daily, btc_signal, tier=tier,
                                     start=a.start, end=a.end, initial_cash=10_000, eligibility=elig,
                                     stress=stress, taker_everywhere=stress)
                    m = r.metrics()
                    rows.append({"candidate": cand, "variant": v or "-", "tier": tier, "stress": stress,
                                 "config": r.config_hash, **{k: m[k] for k in METRIC_KEYS},
                                 "flattens": sum(1 for e in r.governor_events if e["to"] == "FLATTEN")})
                    if not stress:
                        r.equity.to_csv(OUT / f"equity_{cand}_{v or 'base'}_{tier}.csv")
                        r.trades.to_csv(OUT / f"trades_{cand}_{v or 'base'}_{tier}.csv", index=False)
                    RunLog(cli.RUN_LOG).record({"phase": 3, "candidate": cand, "variant": v, "tier": tier, "stress": stress,
                                                "config_hash": r.config_hash, "start": a.start, "end": a.end,
                                                "metrics": {k: x for k, x in m.items() if isinstance(x, (int, float, bool))}})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "insample_metrics.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    show = df[~df.stress][["candidate", "variant", "tier", "net_return", "cagr", "max_drawdown", "calmar", "sharpe",
                           "profit_factor", "expectancy_r", "win_rate", "trade_count", "exposure_pct",
                           "fees_pct_gross_profit", "flattens", "killed"]].copy()
    for c in ("net_return", "cagr", "max_drawdown", "win_rate", "exposure_pct", "fees_pct_gross_profit"):
        show[c] = (show[c] * 100).round(1)
    for c in ("calmar", "sharpe", "profit_factor", "expectancy_r"):
        show[c] = show[c].round(2)
    print(f"== Phase 3 in-sample {a.start}..{a.end}, net of costs; % columns in percent ==")
    print(show.to_string(index=False))
    st = df[df.stress][["candidate", "variant", "tier", "net_return", "max_drawdown", "trade_count"]].copy()
    st["net_return"] = (st.net_return * 100).round(1)
    st["max_drawdown"] = (st.max_drawdown * 100).round(1)
    print("\n== Cost stress (double slippage, taker everywhere) ==")
    print(st.to_string(index=False))

    first = a.candidates.split(",")[0]
    bars, btc_daily, _ = cache[first]
    spec = load_spec(first)
    elig = cli._load_eligibility(_ns(first, None, "T2", a.start, a.end), spec)
    tr = elig[(elig.index >= a.start) & (elig.index <= a.end)]
    basket = sorted(tr.columns[tr.any()])
    alt = benchmark_buy_and_hold({s: bars[s] for s in basket if s in bars}, start=a.start, end=a.end)
    btc = benchmark_buy_and_hold({"BTC": btc_daily}, start=a.start, end=a.end)
    print(f"\n== Benchmarks {a.start}..{a.end} ==")
    for name, eq in (("Equal-weight eligible-alt basket B&H", alt), ("BTC B&H", btc)):
        m = compute_metrics(eq, pd.DataFrame())
        print(f"  {name:<38} return {m['net_return']:+.1%}  max DD {m['max_drawdown']:.1%}  CAGR {m['cagr']:+.1%}")
    print("  Cash                                   return +0.0%  max DD 0.0%")
    ok = (~df.stress) & (df.net_return > 0) & (df.max_drawdown < 0.40)
    print("\nGate G3 (>=1 candidate net-positive after costs with in-sample max DD < 40%):", "PASS" if ok.any() else "FAIL")
    print("passing configs:", [f"{r.candidate}/{r.variant}/{r.tier}" for r in df[ok].itertuples()])


if __name__ == "__main__":
    main()

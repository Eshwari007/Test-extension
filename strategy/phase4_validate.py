"""Phase 4 — out-of-sample validation on the frozen spec.

The hold-out is touched ONCE per candidate: this script runs every surviving variant at every tier on
the hold-out, then the robustness tests. Results go to strategy/runs/phase4/<candidate>/.

    python -m strategy.phase4_validate --candidate C2 --variants V1,V2 [--skip-random]
    python -m strategy.phase4_validate --candidate C2 --variants V1,V2 --random-only --tier T2
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import cli
from .core import validation as V
from .core.backtest import benchmark_buy_and_hold, run_backtest
from .core.config import load_spec
from .core.reporting import RunLog, compute_metrics, format_metrics
from .core.signals import make_strategy

KEYS = ("net_return", "cagr", "max_drawdown", "calmar", "sharpe", "sortino", "profit_factor", "expectancy_r",
        "win_rate", "trade_count", "exposure_pct", "worst_day", "fees_pct_gross_profit", "max_coin_profit_share", "killed")


def _ns(cand, variant, tier, start, end):
    return argparse.Namespace(candidate=cand, variant=variant, tier=tier, data="strategy/data/bars", ref="strategy/data/ref",
                              eligibility="strategy/data", start=start, end=end, cash=10_000.0, stress=False, synthetic=False,
                              n_synthetic=0, benchmarks=False, no_verify=False, out=None, seed=0, mc_runs=0, random_runs=0)


def _log(cand, **entry):
    RunLog(cli.RUN_LOG).record({"phase": 4, "candidate": cand, **entry})


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--candidate", required=True)
    p.add_argument("--variants", default="V1,V2")
    p.add_argument("--tiers", default="T1,T2,T3,T4")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--mc-runs", type=int, default=5000)
    p.add_argument("--random-runs", type=int, default=1000)
    p.add_argument("--random-only", action="store_true")
    p.add_argument("--skip-random", action="store_true")
    p.add_argument("--tier", default="T2", help="tier for the random-entry benchmark")
    a = p.parse_args(argv)

    cand = a.candidate
    spec = load_spec(cand)
    hold = spec.periods["holdout"]
    H0, H1 = hold["start"], hold["end"]
    out = Path(f"strategy/runs/phase4/{cand}")
    out.mkdir(parents=True, exist_ok=True)
    bars, btc_daily, btc_signal = cli._load_bars(_ns(cand, None, "T2", H0, H1), spec)
    elig = cli._load_eligibility(_ns(cand, None, "T2", H0, H1), spec)
    variants = [v if v != "-" else None for v in a.variants.split(",")]
    tiers = a.tiers.split(",")
    run_kw = dict(bars=bars, btc_daily=btc_daily, btc_signal=btc_signal, initial_cash=10_000, eligibility=elig)

    def run(variant, tier, start=H0, end=H1, stress=False, strat=None):
        s = strat or make_strategy(spec.candidate, variant)
        return run_backtest(spec, s, tier=tier, start=start, end=end, stress=stress, taker_everywhere=stress, **run_kw)

    # ------------------------------------------------------------------ random-entry only
    if a.random_only:
        for v in variants:
            t0 = time.time()
            real = run(v, a.tier)
            rnd = V.random_entry_benchmark(spec, make_strategy(spec.candidate, v), real,
                                           {**run_kw, "tier": a.tier, "start": H0, "end": H1},
                                           n_runs=a.random_runs, seed=a.seed)
            res = {"variant": v, "tier": a.tier, "metric": rnd.metric, "real": rnd.real_value, "percentile": rnd.percentile,
                   "n_runs": a.random_runs, "seed": a.seed, "random_p50": float(np.median(rnd.random_values)),
                   "random_p95": float(np.percentile(rnd.random_values, 95)), "passed": rnd.passed(), "seconds": time.time() - t0}
            (out / f"random_entry_{v}_{a.tier}.json").write_text(json.dumps(res, indent=1))
            np.save(out / f"random_entry_{v}_{a.tier}_values.npy", rnd.random_values)
            print(f"{cand} {v} {a.tier}: real {rnd.metric} {rnd.real_value:+.2%} at percentile {rnd.percentile:.1%} "
                  f"(random p50 {res['random_p50']:+.2%}, p95 {res['random_p95']:+.2%}) -> {'PASS' if rnd.passed() else 'FAIL'}  [{res['seconds']:.0f}s]")
            _log(cand, test="random_entry", **{k: res[k] for k in ("variant", "tier", "percentile", "n_runs", "seed")})
        return

    # ------------------------------------------------------------------ 1. hold-out (once) + 4. cost stress
    print(f"== {cand} hold-out {H0}..{H1} — touched once ==")
    rows, results = [], {}
    for v in variants:
        for tier in tiers:
            t0 = time.time()
            r = run(v, tier)
            s = run(v, tier, stress=True)
            results[(v, tier)] = r
            m, ms = r.metrics(), s.metrics()
            rows.append({"variant": v, "tier": tier, **{k: m[k] for k in KEYS}, "stress_net_return": ms["net_return"],
                         "stress_max_drawdown": ms["max_drawdown"], "flattens": sum(1 for e in r.governor_events if e["to"] == "FLATTEN"),
                         "seconds": round(time.time() - t0, 1)})
            r.equity.to_csv(out / f"equity_{v}_{tier}.csv")
            r.trades.to_csv(out / f"trades_{v}_{tier}.csv", index=False)
            _log(cand, test="holdout", variant=v, tier=tier, config_hash=r.config_hash,
                 metrics={k: x for k, x in m.items() if isinstance(x, (int, float, bool))})
            _log(cand, test="holdout_stress", variant=v, tier=tier, config_hash=r.config_hash,
                 metrics={k: x for k, x in ms.items() if isinstance(x, (int, float, bool))})
    df = pd.DataFrame(rows)
    df.to_csv(out / "holdout_metrics.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    show = df[["variant", "tier", "net_return", "cagr", "max_drawdown", "calmar", "sharpe", "sortino", "profit_factor",
               "expectancy_r", "win_rate", "trade_count", "exposure_pct", "fees_pct_gross_profit", "max_coin_profit_share",
               "stress_net_return", "flattens", "killed", "seconds"]].copy()
    for c in ("net_return", "cagr", "max_drawdown", "win_rate", "exposure_pct", "fees_pct_gross_profit", "max_coin_profit_share", "stress_net_return"):
        show[c] = (show[c] * 100).round(1)
    for c in ("calmar", "sharpe", "sortino", "profit_factor", "expectancy_r"):
        show[c] = show[c].round(2)
    print(show.to_string(index=False))

    tr = elig[(elig.index >= H0) & (elig.index <= H1)]
    basket = sorted(tr.columns[tr.any()])
    for name, eq in (("Equal-weight eligible-alt basket B&H", benchmark_buy_and_hold({s: bars[s] for s in basket if s in bars}, H0, H1)),
                     ("BTC B&H", benchmark_buy_and_hold({"BTC": btc_daily}, H0, H1))):
        m = compute_metrics(eq, pd.DataFrame())
        print(f"  {name:<38} return {m['net_return']:+.1%}  max DD {m['max_drawdown']:.1%}  CAGR {m['cagr']:+.1%}")

    # ------------------------------------------------------------------ 5. Monte Carlo + Kelly
    print(f"\n== Monte Carlo ({a.mc_runs} runs, seed {a.seed}) and Kelly ==")
    mc_rows = []
    for (v, tier), r in results.items():
        tr_eq = V.trade_returns_on_equity(r)
        mc = V.monte_carlo(tr_eq, n_runs=a.mc_runs, seed=a.seed)
        k = V.kelly_fraction(tr_eq)
        mc_rows.append({"variant": v, "tier": tier, "dd_p95": mc.dd_p95, "dd_p50": mc.dd_p50, "terminal_p05": mc.terminal_p05,
                        "terminal_p50": mc.terminal_p50, "terminal_p95": mc.terminal_p95, "tier_limit": spec.tiers[tier].max_drawdown,
                        "mc_pass": mc.passed(spec.tiers[tier]), "kelly": k, "half_kelly": k / 2,
                        "risk_per_trade": spec.tiers[tier].risk_per_trade})
    mcdf = pd.DataFrame(mc_rows)
    mcdf.to_csv(out / "monte_carlo.csv", index=False)
    print(mcdf.round(4).to_string(index=False))

    # ------------------------------------------------------------------ 2. walk-forward (full history)
    wf_start = pd.Timestamp("2021-01-01", tz="UTC")
    wf_end = pd.Timestamp(H1, tz="UTC")
    tm, te = spec.periods["walk_forward"]["train_months"], spec.periods["walk_forward"]["test_months"]
    all_variants = list(spec.candidate.get("exit_variants", {}).keys()) or [None]
    print(f"\n== Walk-forward {tm}m train / {te}m test, {wf_start.date()}..{wf_end.date()}, choosing among {all_variants} ==")
    wf_results = {}
    for tier in tiers:
        wf = V.walk_forward(lambda v, s, e: run(v, tier, s, e), all_variants, wf_start, wf_end, tm, te)
        wf_results[tier] = wf
        rows = [{"tier": tier, "test_start": w.test_start.date(), "test_end": w.test_end.date(), "variant": w.chosen_variant,
                 "train_calmar": round(w.train_calmar, 2), "test_pnl": round(w.test_net_pnl, 2), "test_trades": w.test_trades}
                for w in wf.windows]
        pd.DataFrame(rows).to_csv(out / f"walk_forward_{tier}.csv", index=False)
        print(f"  {tier}: {len(wf.windows)} windows, positive {wf.positive_fraction:.0%}, max window share "
              f"{wf.max_window_profit_share:.0%}, chosen: {dict(pd.Series([w.chosen_variant for w in wf.windows]).value_counts())} "
              f"-> {'PASS' if wf.passed() else 'FAIL'}")
        _log(cand, test="walk_forward", tier=tier, windows=len(wf.windows), positive_fraction=wf.positive_fraction)

    # ------------------------------------------------------------------ 3. parameter sensitivity (hold-out)
    print("\n== Parameter sensitivity, +/-25% one at a time, on the hold-out ==")
    sens_rows = []
    for v in variants:
        for tier in tiers:
            sens = V.parameter_sensitivity(make_strategy(spec.candidate, v), lambda s: run(v, tier, strat=s))
            grid = sens.grid.assign(variant=v, tier=tier)
            sens_rows.append(grid)
            worst = grid.loc[grid.calmar.idxmin()] if len(grid) else None
            print(f"  {v} {tier}: baseline Calmar {sens.baseline_calmar:.2f}, worst {sens.worst_ratio:.2f}x "
                  f"({worst.param}={worst.value:g} -> Calmar {worst.calmar:.2f}) -> {'PASS' if sens.passed() else 'FAIL'}")
            _log(cand, test="sensitivity", variant=v, tier=tier, trials=len(grid), worst_ratio=sens.worst_ratio)
    sdf = pd.concat(sens_rows)
    sdf.to_csv(out / "sensitivity.csv", index=False)

    # ------------------------------------------------------------------ 7. breakdown + deflated Sharpe
    print("\n== Regime / tier / coin breakdown (hold-out) and deflated Sharpe ==")
    n_trials = max(RunLog(cli.RUN_LOG).count(), 1)
    bd_rows = []
    for (v, tier), r in results.items():
        b = V.breakdown(r, btc_daily, spec.coin_tier)
        si = V.sharpe_inputs(r.equity)
        dsr = V.deflated_sharpe(r.metrics()["sharpe"], n_trials, si["n_obs"], si["skew"], si["kurt"])
        by_regime = b.get("by_regime", pd.Series(dtype=float))
        by_coin = b.get("by_coin", pd.Series(dtype=float))
        total = float(r.trades.net_pnl.sum()) if len(r.trades) else 0.0
        bd_rows.append({"variant": v, "tier": tier, "bull": by_regime.get("bull", 0.0), "bear": by_regime.get("bear", 0.0),
                        "chop": by_regime.get("chop", 0.0), "top_coin": by_coin.index[0] if len(by_coin) else "",
                        "top_coin_share": (by_coin.iloc[0] / total) if total > 0 and len(by_coin) else np.nan,
                        "bear_loss_vs_limit": (-min(by_regime.get("bear", 0.0), 0.0) / 10_000) / spec.tiers[tier].max_drawdown,
                        "deflated_sharpe": dsr, "trials": n_trials})
        (out / f"breakdown_{v}_{tier}.json").write_text(json.dumps({k: s.round(2).to_dict() for k, s in b.items()}, indent=1))
    bdf = pd.DataFrame(bd_rows)
    bdf.to_csv(out / "breakdown.csv", index=False)
    print(bdf.round(3).to_string(index=False))

    # ------------------------------------------------------------------ hard gates (random-entry filled in later)
    print("\n== Hard gates (random-entry benchmark pending unless already run) ==")
    gate_rows = []
    min_trades = spec.periods["min_oos_trades"][cand]
    for (v, tier), r in results.items():
        mc = mcdf[(mcdf.variant == v) & (mcdf.tier == tier)].iloc[0]
        rnd_file = out / f"random_entry_{v}_{tier}.json"
        rnd = None
        if rnd_file.exists():
            j = json.loads(rnd_file.read_text())
            rnd = V.RandomEntryResult(j["real"], np.load(out / f"random_entry_{v}_{tier}_values.npy"), j["metric"], j["seed"])
        g = V.hard_gates(V.GateInputs(cand, spec.tiers[tier], r.metrics(),
                                      {"net_return": df[(df.variant == v) & (df.tier == tier)].stress_net_return.iloc[0]},
                                      V.MonteCarloResult(a.mc_runs, a.seed, mc.dd_p95, mc.dd_p50, mc.terminal_p05, mc.terminal_p50, mc.terminal_p95),
                                      rnd, wf_results[tier], min_trades))
        if rnd is None:
            g["beats_random_entry"] = None
        gate_rows.append({"variant": v, "tier": tier, **g, "all_pass": all(x for x in g.values() if x is not None) and rnd is not None})
    gdf = pd.DataFrame(gate_rows)
    gdf.to_csv(out / "hard_gates.csv", index=False)
    print(gdf.to_string(index=False))
    print(f"\nTrials counted in the run log: {n_trials}. Gate G4 is decided after the random-entry benchmark.")


if __name__ == "__main__":
    main()

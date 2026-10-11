"""Command line entry point.

  python -m strategy.cli freeze  --reason "Gate G0"
  python -m strategy.cli fetch   --timeframe 1d --start 2021-01-01 --data data/bars          # Alpaca (default)
  python -m strategy.cli quality --timeframe 1d --data data/bars
  python -m strategy.cli backtest --candidate C2 --variant V3 --tier T2 --data data/bars \
          --start 2024-01-01 --end 2026-06-30 [--stress] [--synthetic]
  python -m strategy.cli validate --candidate C2 --variant V3 --tier T2 --data data/bars --synthetic

Every backtest appends one line to runs/run_log.jsonl with the config hash so
the number of trials is counted for the deflated Sharpe ratio.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .core import data as D
from .core.backtest import benchmark_buy_and_hold, run_backtest
from .core.config import SPEC_DIR, freeze_registry, load_spec
from .core.reporting import RunLog, compute_metrics, format_metrics
from .core.signals import make_strategy
from .core import validation as V

RUN_LOG = Path("strategy/runs/run_log.jsonl")


def _universe_symbols(spec) -> list[str]:
    return [s for coins in spec.universe["tiers"].values() for s in coins]


def _load_bars(args, spec):
    """Return (bars, btc_daily, btc_signal) from the store or a synthetic set."""
    tf = spec.candidate["signal_timeframe"]
    if args.synthetic:
        n_days = 900
        syms = _universe_symbols(spec)[: args.n_synthetic]
        btc_daily = D.synthetic_bars(n_days, "1d", seed=1, start="2022-01-01", drift=0.001, vol=0.03, price0=30_000)
        bars = {}
        for i, s in enumerate(syms):
            if tf == "1h":
                bars[s] = D.synthetic_bars(n_days * 24, "1h", seed=100 + i, start="2022-01-01", drift=0.0001, vol=0.012)
            else:
                bars[s] = D.synthetic_bars(n_days, "1d", seed=100 + i, start="2022-01-01", drift=0.001, vol=0.05)
        btc_signal = D.synthetic_bars(n_days * 24, "1h", seed=2, start="2022-01-01", drift=0.00004, vol=0.006, price0=30_000) if tf == "1h" else btc_daily
        return bars, btc_daily, btc_signal
    store = D.BarStore(args.data)
    btc_daily = store.load("BTC", "1d")
    if btc_daily is None:
        sys.exit("No BTC_1d bars in the store; run `fetch` first or pass --synthetic")
    btc_signal = btc_daily if tf == "1d" else store.load("BTC", tf)
    bars = store.load_many(_universe_symbols(spec), tf)
    if not bars:
        sys.exit(f"No {tf} bars for the universe in {args.data}")
    return bars, btc_daily, btc_signal


def cmd_freeze(args) -> None:
    reg = freeze_registry(SPEC_DIR, reason=args.reason)
    print(f"Froze {len(reg['files'])} spec files into {SPEC_DIR / 'REGISTRY.json'}")
    for name, h in reg["files"].items():
        print(f"  {name:<22} {h[:16]}")


def cmd_fetch(args) -> None:
    spec = load_spec("C2", verify=False)
    store = D.BarStore(args.data)
    symbols = ["BTC"] + _universe_symbols(spec)
    for sym in symbols:
        try:
            if args.source == "alpaca":
                df = D.fetch_alpaca_bars(sym, args.timeframe, args.start, args.end)
            else:
                df = D.fetch_coinbase_candles(sym, args.timeframe, args.start, args.end)
        except Exception as exc:  # noqa: BLE001
            print(f"  {sym}: FAILED ({exc})")
            continue
        if df.empty:
            print(f"  {sym}: no data")
            continue
        p = store.save(sym, args.timeframe, df)
        print(f"  {sym}: {len(df)} bars -> {p}")


def cmd_quality(args) -> None:
    spec = load_spec("C2", verify=False)
    store = D.BarStore(args.data)
    listings = D.load_listings(SPEC_DIR / "listings.yaml") if (SPEC_DIR / "listings.yaml").exists() else {}
    failed = []
    for sym in ["BTC"] + _universe_symbols(spec):
        df = store.load(sym, args.timeframe)
        if df is None:
            print(f"  {sym}: missing (excluded)")
            continue
        rep = D.quality_check(sym, args.timeframe, df, listings.get(sym))
        print("  " + rep.summary())
        if not rep.passed:
            failed.append(sym)
    print(f"\nGate G1: {'PASS' if not failed else 'FAIL for ' + ', '.join(failed)}")


def _run(args, spec, strategy, bars, btc_daily, btc_signal, **kw):
    return run_backtest(spec, strategy, bars, btc_daily, btc_signal, tier=args.tier, start=args.start, end=args.end,
                        initial_cash=args.cash, stress=args.stress, **kw)


def cmd_backtest(args) -> None:
    spec = load_spec(args.candidate, verify=not args.no_verify)
    strategy = make_strategy(spec.candidate, args.variant)
    bars, btc_daily, btc_signal = _load_bars(args, spec)
    result = _run(args, spec, strategy, bars, btc_daily, btc_signal)
    m = result.metrics()
    print(f"\n{result.candidate} {result.variant or ''} tier {result.tier} config {result.config_hash}"
          f"{' [STRESS]' if args.stress else ''}{' [SYNTHETIC]' if args.synthetic else ''}")
    print(format_metrics(m))
    if result.governor_events:
        print("  governor events:")
        for ev in result.governor_events:
            print(f"    {ev['time']}: {ev['from']} -> {ev['to']} (dd {ev['drawdown']:.1%})")
    if not args.synthetic or args.benchmarks:
        bh = benchmark_buy_and_hold(bars, args.start, args.end, args.cash)
        bm = compute_metrics(bh, pd.DataFrame())
        print(f"\nEqual-weight alt buy-and-hold: return {bm['net_return']:+.1%}, max DD {bm['max_drawdown']:.1%}")
        btc_bh = benchmark_buy_and_hold({"BTC": btc_daily}, args.start, args.end, args.cash)
        bm = compute_metrics(btc_bh, pd.DataFrame())
        print(f"BTC buy-and-hold:              return {bm['net_return']:+.1%}, max DD {bm['max_drawdown']:.1%}")
    RunLog(RUN_LOG).record({"candidate": result.candidate, "variant": result.variant, "tier": result.tier,
                            "config_hash": result.config_hash, "params": result.params, "synthetic": args.synthetic,
                            "metrics": {k: v for k, v in m.items() if isinstance(v, (int, float, bool))}})
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        result.equity.to_csv(out / "equity.csv")
        result.trades.to_csv(out / "trades.csv", index=False)
        result.decision_log.to_csv(out / "decisions.csv", index=False)
        print(f"\nWrote equity/trades/decisions to {out}")


def cmd_validate(args) -> None:
    """Phase 4 protocol on one candidate/variant/tier. Hold-out dates come from periods.yaml."""
    spec = load_spec(args.candidate, verify=not args.no_verify)
    strategy = make_strategy(spec.candidate, args.variant)
    bars, btc_daily, btc_signal = _load_bars(args, spec)
    hold = spec.periods["holdout"]
    args.start = args.start or hold["start"]
    args.end = args.end or hold["end"]
    tier = spec.tiers[args.tier]

    print(f"== {args.candidate} {args.variant or ''} tier {args.tier} — hold-out {args.start}..{args.end}")
    oos = _run(args, spec, strategy, bars, btc_daily, btc_signal)
    print(format_metrics(oos.metrics()))

    print("\n== Cost stress (double slippage, taker everywhere)")
    args_stress = argparse.Namespace(**{**vars(args), "stress": True})
    stress = _run(args_stress, spec, strategy, bars, btc_daily, btc_signal, taker_everywhere=True)
    print(format_metrics(stress.metrics()))

    print(f"\n== Monte Carlo ({args.mc_runs} runs, seed {args.seed})")
    mc = V.monte_carlo(V.trade_returns_on_equity(oos), n_runs=args.mc_runs, seed=args.seed)
    print(f"  95th-pct max DD {mc.dd_p95:.1%} (tier limit {tier.max_drawdown:.0%}); median terminal {mc.terminal_p50:.3f}x")

    print(f"\n== Random-entry benchmark ({args.random_runs} runs)")
    kw = dict(bars=bars, btc_daily=btc_daily, btc_signal=btc_signal, tier=args.tier, start=args.start, end=args.end,
              initial_cash=args.cash)
    rnd = V.random_entry_benchmark(spec, strategy, oos, kw, n_runs=args.random_runs, seed=args.seed)
    print(f"  real {rnd.metric} {rnd.real_value:+.2%} at percentile {rnd.percentile:.1%} of random runs")

    print("\n== Walk-forward (12m train / 3m test over full history)")
    full_start = min(df.index[0] for df in bars.values()) + pd.Timedelta(days=strategy.warmup_bars() if strategy.signal_timeframe == "1d" else strategy.warmup_bars() // 24 + 1)
    variants = list(spec.candidate.get("exit_variants", {}).keys()) or [None]

    def wf_run(variant, s, e):
        strat = make_strategy(spec.candidate, variant)
        return run_backtest(spec, strat, bars, btc_daily, btc_signal, tier=args.tier, start=s, end=e, initial_cash=args.cash)

    wf = V.walk_forward(wf_run, variants, full_start, pd.Timestamp(args.end, tz="UTC"),
                        spec.periods["walk_forward"]["train_months"], spec.periods["walk_forward"]["test_months"])
    for w in wf.windows:
        print(f"  test {w.test_start.date()}..{w.test_end.date()} variant {w.chosen_variant}: pnl {w.test_net_pnl:+,.0f} ({w.test_trades} trades)")
    print(f"  positive windows {wf.positive_fraction:.0%}, max window share {wf.max_window_profit_share:.0%}")

    print("\n== Parameter sensitivity (+/-25%, one at a time)")
    sens = V.parameter_sensitivity(strategy, lambda s: _run(args, spec, s, bars, btc_daily, btc_signal))
    print(sens.grid.to_string(index=False) if not sens.grid.empty else "  (no parameters)")
    print(f"  worst Calmar / baseline = {sens.worst_ratio:.2f}")

    print("\n== Deflated Sharpe")
    n_trials = max(RunLog(RUN_LOG).count(), 1)
    si = V.sharpe_inputs(oos.equity)
    dsr = V.deflated_sharpe(oos.metrics()["sharpe"], n_trials, si["n_obs"], si["skew"], si["kurt"])
    print(f"  trials counted {n_trials}; P(SR > max random SR) = {dsr:.2f}")

    print("\n== Breakdown")
    for name, series in V.breakdown(oos, btc_daily, spec.coin_tier).items():
        print(f"  {name}:\n" + series.to_string())

    print("\n== Hard gates")
    gates = V.hard_gates(V.GateInputs(args.candidate, tier, oos.metrics(), stress.metrics(), mc, rnd, wf,
                                      spec.periods["min_oos_trades"][args.candidate]))
    for k, v in gates.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    print(f"\nGate G4: {'PASS' if all(gates.values()) else 'FAIL'}")
    print(f"Kelly fraction of trade returns: {V.kelly_fraction(V.trade_returns_on_equity(oos)):.3f} "
          f"(tier risk/trade {tier.risk_per_trade:.3%}; drop the tier if above half-Kelly)")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="strategy")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("freeze")
    f.add_argument("--reason", default="Gate G0 freeze")
    f.set_defaults(fn=cmd_freeze)

    ft = sub.add_parser("fetch")
    ft.add_argument("--source", choices=["alpaca", "coinbase"], default="alpaca",
                    help="alpaca = execution venue (default); coinbase = reference exchange for longer history")
    ft.add_argument("--timeframe", default="1d")
    ft.add_argument("--start", required=True)
    ft.add_argument("--end", default=None)
    ft.add_argument("--data", default="strategy/data/bars")
    ft.set_defaults(fn=cmd_fetch)

    q = sub.add_parser("quality")
    q.add_argument("--timeframe", default="1d")
    q.add_argument("--data", default="strategy/data/bars")
    q.set_defaults(fn=cmd_quality)

    for name, fn in (("backtest", cmd_backtest), ("validate", cmd_validate)):
        b = sub.add_parser(name)
        b.add_argument("--candidate", choices=["C1", "C2", "C3"], required=True)
        b.add_argument("--variant", default=None)
        b.add_argument("--tier", choices=["T1", "T2", "T3", "T4"], default="T2")
        b.add_argument("--data", default="strategy/data/bars")
        b.add_argument("--start", default=None)
        b.add_argument("--end", default=None)
        b.add_argument("--cash", type=float, default=10_000.0)
        b.add_argument("--stress", action="store_true")
        b.add_argument("--synthetic", action="store_true", help="use generated bars (engine checks only)")
        b.add_argument("--n-synthetic", type=int, default=8)
        b.add_argument("--benchmarks", action="store_true")
        b.add_argument("--no-verify", action="store_true", help="skip the registry hash check")
        b.add_argument("--out", default=None)
        b.add_argument("--seed", type=int, default=0)
        b.add_argument("--mc-runs", type=int, default=5000)
        b.add_argument("--random-runs", type=int, default=1000)
        b.set_defaults(fn=fn)

    args = p.parse_args(argv)
    np.set_printoptions(precision=4, suppress=True)
    args.fn(args)


if __name__ == "__main__":
    main()

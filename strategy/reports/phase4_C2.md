# Phase 4 — Out-of-sample validation: C2 (Gate G4)

Hold-out **2024-01-01 → 2026-06-30**, touched once, on the frozen spec (`REGISTRY.json`, C2 hash `622149bb…`).
Variants V1 and V2 (the Gate G3 survivors) at T1–T4: 8 hold-out trials plus 8 cost-stress runs, all
counted in the run log (130 trials at the time of the deflated-Sharpe calculation).
Raw outputs: `phase4_C2_summary.txt`, `phase4_C2_holdout_metrics.csv`, `phase4_C2_hard_gates.csv`,
and `runs/phase4/C2/` (equity, trades, Monte Carlo, walk-forward windows, sensitivity grid, breakdowns).
Reproduce with `python -m strategy.phase4_validate --candidate C2 --variants V1,V2`.

## Verdict: **FAIL — C2 does not go live.**

No variant/tier passes the hard gates. Under the plan a hold-out failure is final for the candidate.

## Hold-out results (net of costs, $10k)

| Variant | Tier | Net return | Max DD | Calmar | Sharpe | PF | Exp. (R) | Win % | Trades | Stress net |
|---|---|---|---|---|---|---|---|---|---|---|
| V1 | T1 | **+1.6 %** | 3.6 % | 0.18 | 0.28 | 1.29 | +0.13 | 50 | 26 | +1.5 % |
| V1 | T2 | +0.2 % | 8.3 % | 0.01 | 0.04 | 1.01 | +0.01 | 45 | 42 | −0.1 % |
| V1 | T3 | −8.3 % | 16.9 % | −0.20 | −0.41 | 0.71 | −0.06 | 39 | 49 | −7.8 % |
| V1 | T4 | −7.4 % | 26.5 % | −0.11 | −0.16 | 0.85 | +0.02 | 40 | 55 | −8.5 % |
| V2 | T1 | −2.8 % | 5.8 % | −0.19 | −0.36 | 0.71 | −0.12 | 29 | 28 | −2.9 % |
| V2 | T2 | −4.9 % | 11.7 % | −0.17 | −0.39 | 0.71 | −0.17 | 26 | 42 | −5.0 % |
| V2 | T3 | −7.0 % | 21.2 % | −0.14 | −0.26 | 0.79 | −0.09 | 28 | 50 | −7.3 % |
| V2 | T4 | −4.3 % | 33.1 % | −0.05 | −0.03 | 0.92 | +0.01 | 31 | 55 | −4.8 % |

Benchmarks on the hold-out: equal-weight eligible-alt basket **−31.9 % (max DD 76.1 %)**; BTC **+32.4 %
(max DD 53.1 %)**; cash 0 %.

## Hard gates

| Gate | Threshold | Result |
|---|---|---|
| Net return after costs > 0 | | V1 T1 and T2 only |
| Max DD ≤ ⅔ tier limit | | all pass |
| Monte Carlo 95th-pct DD ≤ tier limit | 5 000 resamples | all pass |
| Beats random-entry benchmark | > 95th pct | run for V1 T1 (see below); cannot rescue the other gates |
| Walk-forward windows positive | ≥ 60 % | **24–29 %** at every tier (17 windows, 12 m train / 3 m test) |
| Survives double-cost stress | net > 0 | V1 T1 only |
| Minimum OOS trades | 100 | **26–55** at every config |
| Profit concentration | no coin > 30 %, no window > 40 % | fails where profitable (BCH 89 % of V1 T1's profit) |
| Parameter sensitivity | worst Calmar ≥ 50 % of baseline | **fails everywhere**; a 25 % tighter stop flips V1 T1 negative |

Deflated Sharpe: 0.001–0.015 at every config, i.e. the observed Sharpe is indistinguishable from the best
of 130 random trials.

## What the hold-out says about the in-sample result

In-sample (2021–2023) C2 V1/V2 were net-positive at every tier with Calmar up to 0.55. Out of sample
only V1 T1 stays above zero, by 1.6 % over 2½ years, and that comes almost entirely from one coin (BCH)
in one regime (bull). The walk-forward confirms it is not a persistent edge: fewer than a third of the
rolling test windows are positive at any tier, across the whole 2021–2026 history. The breakout signal
with a BTC regime filter is losing money in chop (−288 to −2 177 per config) and only earns it back in
the bull windows.

Claims register updates (results column):

- **K4** (V1 ladder is the best exit): holds — V1 beats V2 and V3 on return/max-DD in and out of sample. Moot, since no variant passes.
- **K8** (BTC regime filter cuts drawdowns): not separately tested; the filter was on in every run.
- **K11** (beats random entries): V1 T1 result recorded in `runs/phase4/C2_random_entry_V1_T1.txt` when the 1 000-run job finishes. Informational.
- **K13** (higher tiers → higher long-run growth): **rejected.** Calmar and net return fall with every tier up, in sample and out.

## Statistical floor

Every config has fewer than the 100 OOS trades the plan requires before a conclusion, so strictly the
result is "insufficient evidence" rather than "disproven". That does not soften the decision: the plan
treats insufficient evidence as not-a-pass, and the walk-forward failure uses the full 5½-year history.

## Where the project stands

- **C3**: retired in Phase 3 (killed at every tier in sample).
- **C2**: fails Gate G4. Retired.
- **C1**: in-sample not yet run; waits on the reference-exchange hourly volume (Coinbase 1h fetch in progress).

If C1 also fails, the project ends with no live strategy, which the plan counts as a success: the cost was
research time, not capital. Any change to a candidate's parameters is a new strategy and starts again at
Phase 3 on the training period — the hold-out stays untouched for it, since it has now been seen.

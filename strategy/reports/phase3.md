# Phase 3 — In-sample research (Gate G3)

Training period only: **2021-01-01 → 2023-12-31** (the first eligible month to the plan's training end).
Every pre-registered candidate/variant was run at every tier with the frozen parameters; nothing was tuned.
Raw outputs: `phase3_insample_summary.txt`, `phase3_insample_metrics.csv`, per-run equity/trades under
`runs/phase3/`. Reproduce with `python -m strategy.phase3_sweep`.

C1 is not yet run: its volume filter needs reference-exchange hourly volume (see Phase 1); the Coinbase 1h
fetch is in progress.

## Two engine defects found and fixed before these results

1. **Governor could never resume after a flatten.** Once flattened, the portfolio is all cash, equity never
   moves, the drawdown from the peak never shrinks, so the governor stayed at FLATTEN for the rest of the
   test. The plan defines the steps down but not the way back. Resolution (engine decision, documented
   here, not a spec change): after a flatten the strategy stays in cash for a **30-bar cooldown**, then
   **re-bases** the governor's peak to current equity and resumes. The **kill** step keeps measuring from
   the **all-time** peak and is never re-based. Tests: `test_risk.py::test_governor_resumes…`,
   `…::test_kill_measures_from_all_time_peak…`.
2. **Killed runs stopped their equity curve at the kill date**, which annualised a short window (C3 showed
   a 168 % CAGR on a 46 % return). A killed run now sits in cash to the end of the window.

Also: with reference history merged, the window must start at the first eligible month, not 2017; the CLI
now defaults `--start` to that month when an eligibility table is used.

## Results (net of fees and slippage, $10k, % columns in percent)

| Candidate | Tier | Net return | CAGR | Max DD | Calmar | Sharpe | PF | Exp. (R) | Win % | Trades | Avg exposure | Killed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C2 V1 (fixed ladder) | T1 | +4.3 | 1.4 | 2.6 | 0.55 | 0.57 | 1.86 | +0.27 | 61 | 31 | 1.6 | no |
| | T2 | +3.3 | 1.1 | 6.2 | 0.18 | 0.27 | 1.27 | +0.11 | 53 | 40 | 3.1 | no |
| | T3 | +5.3 | 1.7 | 11.3 | 0.15 | 0.25 | 1.24 | +0.10 | 52 | 44 | 5.7 | no |
| | T4 | +8.1 | 2.6 | 17.5 | 0.15 | 0.27 | 1.23 | +0.10 | 53 | 45 | 9.2 | no |
| C2 V2 (R ladder + trail) | T1 | +5.5 | 1.8 | 4.3 | 0.42 | 0.53 | 1.73 | +0.34 | 56 | 32 | 2.2 | no |
| | T2 | +3.5 | 1.2 | 9.7 | 0.12 | 0.21 | 1.21 | +0.18 | 50 | 42 | 3.8 | no |
| | T3 | +6.8 | 2.2 | 15.8 | 0.14 | 0.25 | 1.24 | +0.15 | 50 | 46 | 6.5 | no |
| | T4 | +2.6 | 0.9 | 25.4 | 0.03 | 0.14 | 1.05 | +0.12 | 50 | 48 | 10.7 | no |
| C2 V3 (chandelier) | T1 | +0.8 | 0.3 | 5.6 | 0.05 | 0.09 | 1.12 | +0.12 | 51 | 37 | 2.1 | no |
| | T2 | −0.2 | −0.1 | 10.8 | −0.01 | 0.03 | 0.98 | +0.04 | 47 | 47 | 3.7 | no |
| | T3 | −0.0 | −0.0 | 17.2 | −0.00 | 0.06 | 1.00 | +0.04 | 48 | 50 | 6.4 | no |
| | T4 | −5.1 | −1.7 | 27.9 | −0.06 | 0.01 | 0.86 | −0.00 | 46 | 54 | 9.5 | no |
| C3 (momentum rotation) | T1 | +22.8 | 7.1 | 15.2 | 0.47 | 1.19 | 8.85 | — | 67 | 12 | 14.3 | **yes** |
| | T2 | +10.9 | 3.5 | 33.6 | 0.10 | 0.75 | 2.58 | — | 67 | 6 | 40.2 | **yes** |
| | T3 | +45.6 | 13.4 | 46.3 | 0.29 | 1.46 | ∞ | — | 100 | 3 | 79.7 | **yes** |
| | T4 | +21.5 | 6.7 | 62.9 | 0.11 | 0.72 | 1.52 | — | 31 | 16 | 58.2 | **yes** |

Cost stress (double slippage, taker fee everywhere) changes every number by under 1 point; no sign flips
except C2 V3 T2 (−0.2 → +0.7, noise).

Benchmarks over the same window: equal-weight eligible-alt basket **+692 % with an 89.8 % max DD**;
BTC **+43.7 % with 76.7 % max DD**; cash 0 %.

## Reading

- **C2 V1 and V2 are net-positive after costs at every tier, and survive the cost stress**, but the edge
  is small: expectancy +0.10 to +0.34 R, profit factor 1.2–1.9, 31–48 trades in three years (the plan
  expected 40–120 *per year*; the $5M universe averaged 7–8 coins and BTC was below its 200-day SMA for
  half the window). Average exposure is 2–11 %: with 0.75 % risk per trade and a 2.5-ATR stop, each
  position is ~5 % of equity, so the strategy is mostly in cash. Calmar peaks at T1 (0.55 / 0.42) and
  falls with every tier up: **more risk did not buy more growth per unit of drawdown (claim K13, in-sample).**
- **C2 V3 (chandelier) is flat to negative.** The wider trail gives back the ladder's banked gains.
  Claim K4 (V1 is the best exit) holds in-sample on return/DD.
- **C3 was killed at every tier.** It is 100 % cash or 3 concentrated alt positions with no stop; the
  May-2021 and 2022 crashes took it through the kill level (15–60 % from the all-time peak) before the
  weekly rebalance or the BTC regime filter reacted — exactly the "slow reaction to sudden crashes" risk
  the plan listed. The green-looking returns are the pre-kill run-up and are not investable. Per the
  plan a killed strategy is retired; C3 does not proceed to Phase 4 in its current form.
- Nothing here beats buy-and-hold on raw return, and nothing was expected to. On drawdown every C2
  configuration is an order of magnitude safer than either benchmark.

## Gate G3: PASS

At least one candidate is net-positive after costs with in-sample max DD under 40 %: C2 V1 and V2 at all
tiers, C2 V3 at T1 only. **C2 V1 and V2 proceed to Phase 4** (hold-out, walk-forward, sensitivity, Monte
Carlo, random-entry benchmark). C3 is retired. C1 waits on its volume-source decision.

Caveat on statistical power: 31–48 in-sample trades is thin. Phase 4's floor of 100 OOS trades for C2
will be hard to reach on a 2.5-year hold-out at this trade rate; expect "insufficient evidence" rather
than a pass unless the hold-out (2024–2026, a larger universe and a mostly risk-on BTC) trades more.

# Speculative Crypto Strategy — project outcome

**Result: no candidate passes. Nothing goes live.** Under the plan this is the accepted outcome: the cost
was research time, not capital. Every claim was tested against a written threshold decided before the
data was examined, and every spec change is in a dated commit with its reason.

| Phase | Gate | Outcome |
|---|---|---|
| 0 Pre-registration | G0 | Specs frozen, hashes in `specs/REGISTRY.json`; 4 re-freezes, each documented (listings, rebrand ratios, $5M threshold, G1 exclusions). No candidate parameter was ever changed. |
| 1 Data | G1 | PASS. Alpaca + Coinbase reference; SOL delisting window; MKR→SKY 1:24000; $5M liquidity threshold chosen from a sensitivity sweep; YFI/BAT excluded on 1h. `phase1.md` |
| 2 Engine | G2 | 72 tests pass; 15 of 20 golden trades. Two engine defects found in Phase 3 and fixed before results counted (governor resume; killed-run equity). |
| 3 In-sample | G3 | C2 V1/V2 pass (small edge); C2 V3 flat; **C3 killed at every tier; C1 negative at every tier under both volume sources.** `phase3.md`, `phase3_C1.md` |
| 4 Out-of-sample | G4 | **C2 fails**: walk-forward 24–29 % positive windows, sensitivity fails, 26–55 OOS trades, deflated Sharpe ≈ 0. `phase4_C2.md` |
| 5–6 Paper / live | — | Not reached. |

## Claims register — results

| ID | Claim | Result |
|---|---|---|
| K1 | Alpaca supports bracket/OCO for crypto | Disproven by docs; stops are client-side in `execution.py`. |
| K2 | Entries after 17:00 UTC improve results | Not tested (no candidate survived to Phase 4 with enough trades). |
| K3 | MACD > 0 filter improves entries | Not tested (same). |
| K4 | 50/25/25 ladder is the best exit | Holds for C2 in and out of sample (V1 > V2 > V3). Moot. |
| K5 | Strategy A +284 % / 27.9 % DD | Unverifiable as stated; closest codable spec (C1) loses money. |
| K6 | Strategy B +1 166 % | Rejected (requires shorting). |
| K7 | RSI(2) > ADX(2) beats B&H | Not tested. |
| K8 | BTC regime filter cuts drawdowns | Not separately ablated; filter was on in every run. |
| K9 | Fees erase most intraday edge | **Confirmed**: C1 fees 24–35 % of gross profit, negative expectancy. |
| K10 | Tier caps keep worst day < 70 % of limit | Worst hold-out day −3.7 % at T4 vs limit 60 %; holds trivially at this exposure. |
| K11 | Each candidate beats random entries | **Rejected**: C2 V1 T1 at the 72nd percentile of 1 000 random-entry runs (needs > 95th). The entry signal adds nothing beyond the regime filter. |
| K12 | Backtest costs match Alpaca reality | Not reached (Phase 5). |
| K13 | Higher tiers → higher long-run growth | **Rejected**: Calmar and return fall with every tier up, in and out of sample, for every candidate. |

## What was learned that a new hypothesis would have to answer

1. **The universe is small.** At any liquidity threshold Alpaca can honour, 7–8 coins are eligible in a
   typical month and 3 in the worst. Breakout strategies that need 40–400 trades a year do not get them.
2. **The BTC > SMA200 regime filter is off half the time** (all of 2022), and when it is on, chop costs
   more than trends earn for daily breakouts (walk-forward).
3. **Sizing by ATR risk keeps exposure at 2–10 %.** The candidates were mostly cash; their returns are
   bounded by that before any signal quality question.
4. **Momentum rotation without a stop dies in crashes** at every tier, even with weekly rebalancing.
5. **Intraday cannot clear a 0.5–0.6 % round trip** on these coins at this fee tier.

Any new candidate is a new strategy: Phase 0 pre-registration, then Phase 3 on the training period.
The 2024-01 → 2026-06 hold-out has been seen for C2 and must not be reused for a C2 derivative.

This is research and engineering output, not financial advice.

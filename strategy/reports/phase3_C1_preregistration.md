# C1 — pre-registered data variants (written before any C1 run on real data)

Phase 1 showed Alpaca's own hourly volume is unusable for C1's entry filter (*1h volume > 2× its 7-day
average*): most coins have no trades at all in 18–76 % of hours on Alpaca. The spec's parameters are
unchanged; only the **source of the volume series** is a data choice the plan did not fix. Both options
are registered here, in this commit, and both will be run and reported:

| Variant | Prices | Volume used by the entry filter |
|---|---|---|
| `alpaca` | Alpaca 1h (reference 1h before listing) | Alpaca venue volume |
| `reference` | Alpaca 1h (reference 1h before listing) | Coinbase 1h volume (`overlay_volume`) |

Everything else (regime filter, breakout, stop, exit, tiers, costs, eligibility) is identical and frozen.
Both variants count as trials in the run log. Selection rule: a variant passes Gate G3 on its own merits;
if both pass, the one with the higher in-sample Calmar at T1 goes forward, ties to `reference`.
YFI and BAT are excluded on 1h (Gate G1). BTC's hourly regime series uses Alpaca bars with Coinbase bars
before 2021.

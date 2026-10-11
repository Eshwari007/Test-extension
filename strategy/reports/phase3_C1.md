# Phase 3 — In-sample research: C1 intraday (Gate G3)

Training period 2021-01-01 → 2023-12-31, 1h signal bars, frozen parameters, both pre-registered data
variants (`phase3_C1_preregistration.md`). YFI and BAT excluded on 1h (Gate G1). Reference 1h bars:
Coinbase, G1 PASS except LDO and WIF (1.2 % missing), which are never eligible at $5M anyway.
Raw: `phase3_C1_insample_volalpaca.txt`, `phase3_C1_insample_volref.txt`, `runs/phase3/*C1*`.

## Results (net of costs, $10k)

| Volume source | Tier | Net return | Max DD | PF | Exp. (R) | Win % | Trades | Fees / gross profit |
|---|---|---|---|---|---|---|---|---|
| Alpaca venue | T1 | −7.0 % | 8.0 % | 0.50 | −0.39 | 23 | 47 | 32 % |
| | T2 | −11.9 % | 13.3 % | 0.47 | −0.42 | 22 | 49 | 35 % |
| | T3 | −19.2 % | 21.2 % | 0.59 | −0.33 | 25 | 65 | 30 % |
| | T4 | −29.3 % | 32.1 % | 0.60 | −0.33 | 25 | 72 | 30 % |
| Coinbase reference | T1 | −5.1 % | 7.3 % | 0.76 | −0.17 | 31 | 78 | 24 % |
| | T2 | −9.9 % | 12.3 % | 0.74 | −0.18 | 30 | 90 | 26 % |
| | T3 | −16.6 % | 19.7 % | 0.75 | −0.25 | 30 | 105 | 27 % |
| | T4 | −25.8 % | 29.9 % | 0.79 | −0.22 | 31 | 146 | 26 % |

Cost stress changes nothing material. Benchmarks: alt basket +1 388 % (DD 90 %), BTC +43.7 % (DD 77 %).

## Reading

- **Negative expectancy at every tier, with either volume source.** The reference-volume variant is
  cleaner (more trades, higher PF, higher win rate) but still loses −0.17 to −0.25 R per trade.
- **Fees are 24–35 % of gross profit.** With a 1.5-ATR stop and a +2R target on hourly bars the average
  win is a few percent, and the ~0.6 % round trip is a large share of it. This is claim **K9**, confirmed:
  intraday on Alpaca's fee tier does not clear costs.
- Trade counts (47–146 in three years) are far below the plan's 150–400 per year: the double regime
  filter (BTC daily > SMA200 *and* BTC 1h > SMA100) plus a 2× volume spike is rarely true at once on a
  7–8-coin universe.
- Exposure is 0.2–2 %: the strategy is almost always in cash, and still loses.

## Gate G3: FAIL. C1 is retired. No hold-out run is made for C1 (nothing to validate).

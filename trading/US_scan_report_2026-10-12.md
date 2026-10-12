# Gajjala Momentum Scanner (US) - replay results, week of Oct 5-9, 2026

Data: Alpaca SIP feed (full consolidated volume), split-adjusted daily bars from 2025-11-26,
5-minute bars for the last five sessions, regular hours only (9:30-16:00 ET).
Universe: 503 S&P 500 names (list current to the Oct 6, 2026 addition) plus 13 Nasdaq 100
names not in the S&P 500 (SHOP, ARM, MSTR, MELI, PDD, ASML, AZN, TEAM, ZS, CCEP, GFS, TTD, CRWV).
MP blacklisted as in the spec. 516 symbols total; all had Alpaca data.

Method: for each session, Stage 1 was run on daily bars through the previous close and the
top 15 were passed to Stage 2. Stage 2 evaluated every 5-minute bar of that session (not just
the latest bar), so this is the complete set of signals the scanner would have produced if it
had run every 5 minutes.

## Full signals (all 8 checks passed)

| Session | Time (ET) | Ticker | Entry | Stop | Risk % | Qty (100k acct, 0.5% risk) | T1 / T2 / T3 | Pole | Flag range | Vol vs 20-bar |
|---|---|---|---|---|---|---|---|---|---|---|
| Oct 5 | 14:05 | MRNA | 204.63 | 202.26 | 1.16% | 210 | 209.75 / 215.88 / 225.09 | +1.75% | 1.00% | 1.68x |
| Oct 9 | 13:20 | CIEN | 452.26 | 446.72 | 1.22% | 90 | 463.56 / 477.13 / 497.48 | +1.75% | 1.00% | 1.62x |

Outcome of those two trades (stop = flag low, no overnight hold):
- MRNA: stopped out at 15:30 the same day (low 201.63). It then gapped up and hit T1 at 9:35 on Oct 6
  and T2 on Oct 9, but only a position held overnight would have captured that.
- CIEN: stopped out at 15:00 the same day (low 446.33). Closed at 449.75.

Net: 2 signals, 2 stops, roughly -2R for the week.

## Near misses (7 of 8 checks on at least one bar)

The pole check (6 bars rising at least 1.5%) was the one that failed almost every time.
Tight flags, breakouts and volume were common; a 1.5% six-bar pole on a large cap is rare.

- Oct 5: P, HPE, CRWD, MSTR, ILMN (all failed only the pole)
- Oct 6: P, HPE (pole); AMD (volume)
- Oct 7: CIEN, AMD, MRNA, LITE, MRVL, ZS, NTAP (pole); P (breakout)
- Oct 8: none reached 7 of 8
- Oct 9: P, ZS, SHOP, ILMN, CRWD, NTAP, RVTY, CDNS, DDOG, TWLO, HPE (pole); MRNA (flag range)

## Stage 1 leaders by session (top 15 by 21-day return among names passing the filters)

Oct 5 (as of Oct 2 close, 105 of 515 pass): P, AMD, HPE, BE, CRWD, INTC, DDOG, MRVL, TER, ARM, TWLO, MSTR, ILMN, MRNA, COHR
Oct 6 (as of Oct 5 close, 108 pass): P, AMD, MRNA, ILMN, TER, MRVL, LITE, DDOG, PTC, CRWD, INTC, COHR, HPE, TWLO, ARM
Oct 7 (as of Oct 6 close, 118 pass): P, CIEN, PTC, AMD, HPE, CRWD, DDOG, MRNA, LITE, MRVL, SNPS, PANW, ILMN, ZS, NTAP
Oct 8 (as of Oct 7 close, 120 pass): P, PTC, MRNA, ZS, CIEN, DDOG, HPE, SNPS, AMD, ILMN, CRWD, MRVL, CDNS, NTAP, SHOP
Oct 9 (as of Oct 8 close, 122 pass): P, PTC, MRNA, ZS, SHOP, ILMN, SNPS, CRWD, CIEN, NTAP, RVTY, CDNS, DDOG, TWLO, HPE

## Watchlist for Monday Oct 12 (Stage 1 as of Oct 9 close; SPY 21-day +2.74%; 134 of 515 pass)

| Rank | Ticker | Close | 21d return | vs SPY | Off 52w high | 20d avg $ volume |
|---|---|---|---|---|---|---|
| 1 | MRNA | 225.00 | +64.7% | +62.0% | 0.0% | $3.29B |
| 2 | P | 154.49 | +64.2% | +61.4% | -1.6% | $968M |
| 3 | PTC | 194.45 | +51.1% | +48.3% | -0.8% | $697M |
| 4 | ZS | 233.73 | +43.0% | +40.2% | -13.5% | $689M |
| 5 | ILMN | 278.17 | +38.2% | +35.5% | -10.1% | $1.15B |
| 6 | SHOP | 170.85 | +35.0% | +32.2% | -1.2% | $1.39B |
| 7 | CIEN | 449.77 | +34.4% | +31.7% | -29.4% | $1.13B |
| 8 | HPE | 73.46 | +33.0% | +30.3% | -0.1% | $1.31B |
| 9 | DDOG | 293.26 | +32.3% | +29.5% | -0.3% | $796M |
| 10 | CRWD | 275.04 | +31.7% | +28.9% | -4.2% | $2.70B |
| 11 | NTAP | 237.15 | +29.2% | +26.4% | -0.4% | $546M |
| 12 | SNPS | 509.99 | +28.4% | +25.7% | -5.5% | $1.13B |
| 13 | RVTY | 154.18 | +27.5% | +24.7% | -7.3% | $348M |
| 14 | PLTR | 209.05 | +26.0% | +23.3% | -0.3% | $4.52B |
| 15 | TWLO | 289.47 | +25.2% | +22.5% | -6.1% | $1.33B |

All 15 are also above their 200-day SMA, so REQUIRE_200SMA=True would not change this list.

## Notes on the strategy document

- The names the PDF lists as candidates (BSP, HAE, PENG, UTHR) are not in the S&P 500 or Nasdaq 100,
  so the scanner as specified can never see them. SNDK and MU are in the universe but did not make the
  top 15 by 21-day return this week.
- The pole requirement is the binding constraint. 0 of 15 leaders met it on most bars. If the intent is
  to trade more setups, that is the parameter to loosen (or measure the pole over more bars).
- Signals fire at the close of a 5-minute bar; entry assumes a fill at that close.
- Not financial advice. Two trades is not a sample; both stops were hit within two hours.

## Files
- gajjala_scanner_us.py: the replay scanner (requests + pandas, no alpaca-py needed behind the proxy)
- us_intraday_setups.csv: the two signals with every check's result
- us_best_bar_per_leader.csv: best bar per leader per session with check-by-check results
- us_momentum_leaders.csv: Stage 1 top 15 for each session
- us_momentum_leaders_for_2026-10-12.csv: Monday's watchlist
- us_stage1_all_symbols_2026-10-09.csv: all 515 symbols with Stage 1 metrics as of Friday's close

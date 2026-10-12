# Gajjala US scanner - September 2026 backtest

Account $100,000, 0.5% risk per trade ($500), Alpaca SIP data, S&P 500 + Nasdaq 100 universe.
Stage 1 run as of each prior close; every 5-minute bar of each session checked (21 sessions).
Exits per the PDF: stop at flag low, scale out 1/3 at T1 +2.5%, T2 +5.5%, T3 +10%, trail under EMA9
once +1R. Entry at signal-bar close, no commissions or slippage. One open trade per symbol.

## Strategy exactly as specified (pole >= 1.5%)

| Date | Time ET | Ticker | Entry | Stop | Qty | Exit | P&L |
|---|---|---|---|---|---|---|---|
| Sep 4 | 12:50 | SMCI | 40.84 | 40.45 | 1265 | Stopped 13:00 | -$499.67 |
| Sep 28 | 13:10 | MSTR | 161.07 | 158.44 | 190 | Stopped 15:15 | -$499.70 |

Total: -$999.37 (-1.00%), 2 trades, 0 wins, -2.0R. Same result whether flat at close or held overnight
(both stopped within two hours).

## Sensitivity: loosen the pole requirement

| Pole min | Flat at close | Hold overnight, trail |
|---|---|---|
| 1.5% (spec) | 2 trades, 0 wins, -$999 (-1.0%) | 2 trades, 0 wins, -$999 (-1.0%) |
| 1.0% | 5 trades, 1 win, -$1,298 (-1.3%) | 6 trades, 2 wins, +$2,500 (+2.5%) |
| 0.75% | 9 trades, 3 wins, -$974 (-1.0%) | 10 trades, 4 wins, +$2,833 (+2.8%) |

The overnight gains come almost entirely from one trade: MSTR signalled at 15:55 on Sep 18 and gapped
up Monday Sep 21, hitting all three targets at the open (+$3,799, +7.6R). The same overnight rule also
produced a -3.7R gap-down loss on MSTR on Sep 3-4. Strip the one gap and overnight holding is roughly flat.

## Read

- As written, the strategy traded twice in September and lost both times: about -$1,000 on $100k.
- The intraday version loses money at every pole setting tested. Winners get cut by the trail or the
  close before reaching T2/T3, while losers reliably hit the full -1R.
- Any positive number depends on holding overnight and catching a gap, which the PDF's rules do not do.
- 2 to 10 trades is far too few to call it an edge either way. The Sep 5 - Oct 9 combined sample is
  4 trades, 0 wins, -$2,000 at spec settings.

Files: backtest.py (engine), backtest_2026-09-01_2026-09-30_intraday.csv / _overnight.csv (spec trades),
backtest_sep_pole1.0_*.csv and backtest_sep_pole0.75_*.csv (sensitivity trade lists).

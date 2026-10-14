# Validation verdict against the seven-test bar

Date: Oct 13 2026. Tests 1 to 4 run here; 5 to 7 need the engine and a paper book and are described
at the end. All numbers: next-open fills, 5 bps per side, ranked slot filling, SPY-above-EMA50 regime
switch, trend book only unless stated. Scripts and logs are under `research/` (`test1_recon.py`,
`test4_demeaned.py`, `pit_data.py`, `test23_pit.py`, `attribution.py`, `out/test*.log`, `out/attribution.log`).

## The verdict in one line

**It does not pass.** With point-in-time index membership the trend book beats SPY in 3 of 6 years at
best, has a profit factor below 1.0 in 2023, and about half of the edge I reported earlier was
survivorship bias from using today's constituent list. It is a low-beta sleeve that protects in a
bear and lags in a broad bull, not a 50%-a-year strategy. I would not build the real-money engine
for it as specified.

## Test 1: reconciliation replay, Jun 23 to Oct 9 2026

SPY +6.1% over the 77 sessions.

| Book | Result | Trades | PF |
|---|---|---|---|
| Trend 10 x 10%, ranked, regime | **+2.3%** | 40 | 1.20 |
| Trend 20 x 5%, ranked, regime | -2.9% | 80 | 0.80 |
| Swing 10 x 10%, regime | +2.1% | 44 | 1.37 |
| Raw candidate set (176 breakout signals, before slots) | avg -1.58% per trade | 176 | 0.53 |

The sim is marginally positive at 10 x 10% and negative at 20 x 5%. The raw signal set on this tape
was net losing; the rank filter extracted the few winners (MRNA +50% from Aug 20, CRWD +18%, TRV +17%,
ILMN +12%). Full trade lists: `out/test1_trend_10x10.csv`, `test1_trend_20x5.csv`, `test1_swing.csv`,
to put beside the mom engine's 20 real trades.

Rule differences I can name from the list:
- **MRNA was bought twice, not blocked by the 52-week filter.** Jul 6 at 78.59, stopped out by the
  EMA21 exit Jul 17 at -21.6% (the biggest single loss in the window); Aug 20 at 150.22, still open at
  +50%. Whether the mom engine missed the second entry depends on its own filters; the plan's rules took it.
- **Ranked fill did buy MPC (Sep 21, -6.0%, EMA21 exit three days later).** PSX and VLO never produced
  a trend breakout signal in the window; the swing book traded both (PSX -0.5R, VLO +0.4R).
- The June 23 to 25 cluster (DHI, PHM, UAL, LUV, AMAT, TER, GLW, APH) lost 8 to 15% each within two
  weeks: a post-rally breakout burst that failed. That cluster alone is -5 points on the 20 x 5% book.

Verdict on test 1: survives narrowly at 10 x 10%, fails at 20 x 5%, and the raw signal quality on this
tape was poor. "2026 is a different regime" is partly right: the H1 2026 theme carried the year.

## Test 2: 2022 with point-in-time constituents

Universe: S&P 500 membership on each date from the Clenow/fja05680 history (632 names since mid-2020,
627 with Alpaca daily data, so delisted names are in). Cache `research/cache_pit/`.

| 2022, trend 20 x 5% ranked | Total | Max DD | PF | Trades |
|---|---|---|---|---|
| Regime switch ON | **-0.2%** | -6.8% | 0.97 | 123 |
| Regime switch OFF | -2.8% | -13.2% | 0.89 | 186 |
| SPY | -19.9% | -25.4% | | |

The switch blocked entries on 163 of 251 sessions and did visible work: drawdown halved, loss cut.
The book lost far less than SPY. **PF 0.97 fails the ≥ 1.1 bar.** Half pass: the bear protection
is real, the edge in a bear is not.

## Test 3: six windows, point-in-time universe

Primary run without the -8% disaster stop (it was never part of the validated rules; the plan added it
as a safety and it costs about 10 points over 2025-26, see attribution below). With the stop:
`out/test23_pit.log`.

| Window | SPY | Trend 20 x 5% | Excess | Max DD | PF | Trend 10 x 10% | Excess | PF |
|---|---|---|---|---|---|---|---|---|
| 2021 | +28.7% | +15.0% | -13.7 | -11.5% | 1.34 | +9.8% | -18.9 | 1.17 |
| 2022 | -19.9% | -0.2% | **+19.8** | -6.8% | 0.97 | +3.5% | **+23.5** | 1.26 |
| 2023 | +24.8% | -2.7% | -27.5 | -11.1% | **0.82** | -6.0% | -30.8 | **0.79** |
| 2024 | +24.0% | +15.5% | -8.5 | -6.1% | 1.67 | +28.8% | **+4.8** | 2.12 |
| 2025 | +16.6% | +9.3% | -7.3 | -7.0% | 1.64 | +10.5% | -6.1 | 1.82 |
| 2026 YTD | +14.0% | +13.6% | -0.3 | -14.0% | 1.55 | +27.4% | **+13.4** | 2.12 |

Against the bar (positive excess in ≥ 4 of 6, worst DD ≤ 25%, PF ≥ 1.2 in every window):

| | 20 x 5% | 10 x 10% |
|---|---|---|
| Windows with positive excess | **1 of 6** | **3 of 6** |
| Worst drawdown | -14.0% (pass) | -16.3% (pass) |
| Minimum PF | 0.82 (fail) | 0.79 (fail) |
| Mean excess per year | -6.3 pp | -2.4 pp |

**Fails on two of three criteria in both sizings.** The worst window is 2023, a broad bull year in
which momentum breakouts lost money outright. 2021 lags by 14 to 19 points. The strategy is
positive in every year except 2022 and 2023 but only beats the index when the market is narrow
(2024, 2026) or falling (2022).

Returns I would now believe: SPY minus 2 to 6 points a year with roughly 60% of SPY's drawdown,
and a strong 2022-style year when the switch is off most of the time. That is a defensive sleeve,
not an alpha engine.

## Test 4: day-demeaned entry edge

20-session forward return of each trend entry signal minus SPY over the same sessions, next-open fills.

| Universe | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| Point-in-time S&P 500 | -0.33% | +1.35% | -0.99% | -0.45% | +0.22% | +0.44% |
| Today's list (the earlier studies) | | | -0.49% | +0.97% | +1.43% | +1.98% |

With today's list the entry carried +1.67% excess at 20 days over 2025-26 with t = 5.9, and +0.42%
over 2023-24 (t = 2.2). With point-in-time membership the same entry is positive in 3 of 6 years and
negative in 2021, 2023 and 2024. The stocks engine's lesson applies here too: most of the apparent
entry edge was the tape and the universe, not the rule. What survives is the 2022 number: when the
market is falling, the breakouts that still happen carry +1.35% excess, which is the regime switch
and the 52-week-high filter selecting the few real leaders.

## Attribution: where the earlier +57% to +73% came from

2025-01-02 to 2026-10-09, trend 20 x 5% ranked + regime (`out/attribution.log`):

| Universe | Disaster stop | Candidates | Cand. avg | Portfolio | Max DD |
|---|---|---|---|---|---|
| Point-in-time S&P 500 | -8% | 1,205 | +0.12% | +23.2% | -16.0% |
| Point-in-time S&P 500 | none | 1,193 | +0.39% | **+32.7%** | -14.6% |
| Today's list + NDX extras | -8% | 1,286 | +0.88% | +63.4% | -16.6% |
| Today's list + NDX extras | none | 1,271 | +1.20% | **+72.3%** | -14.5% |

SPY did +33.2%. With honest membership and no stop the trend book matched the index with a smaller
drawdown; the 40-point gap to the earlier figure is the universe. 25 names were tradeable only with
today's list (not S&P 500 members at signal time): ARM, SHOP, MELI, ASML, AZN, CCEP, GFS, TEAM, ZS
(Nasdaq-100 names the plan legitimately includes, but for which I have no point-in-time membership),
and APP, BE, CIEN, CRH, CVNA, ECHO, FERG, FLEX, HOOD, ILMN, MRVL, P, RDDT, TWLO, VRT (added to the
index after they had already run, or never members). Those 77 candidate trades averaged +9.3% and
contributed 714 of the 1,529 percentage points of raw candidate return. That is survivorship bias
in its purest form: the list of today's members is a list of stocks that went up.

The -8% disaster stop costs 9 to 10 points in both universes. It should be removed from the plan;
the EMA21 exit is the stop.

## What I got wrong, specifically

1. I called the trend edge "stable across four years" on a universe that could not show otherwise.
   The point-in-time test was the first one that could, and it did.
2. I reported the swing + trend combination at +111% and +58% without a point-in-time universe and
   without the 2021 and 2023 windows, both of which the trend book lags badly.
3. I added a disaster stop to the plan on judgment, not evidence. It hurts.
4. The swing book was never run on point-in-time membership (it needs 5-minute bars for every
   historical member). Given its 2023-24 result on the favourable universe (PF 1.2), it would not
   change the verdict.

## Tests 5 to 7

Not run; they need the engine. Their definitions stand as written in the plan and in your message:
fixture regression plus a one-month replay through the engine's own code path with ≥ 90% trade-list
match before any paper; paper judged at n ≥ 60 or 2026-12-31 on `seeded=0` rows with PF ≥ 1.2 and
≥ 90% fill match; real at reduced size for a quarter only after that, judged against the stocks
engine on the same capital. Given tests 2 to 4, I would not start test 5 for this rule set.

## What would be worth doing instead

- If a defensive momentum sleeve is wanted: the 2022 result (flat while SPY lost 20%, 7% drawdown) is
  the one real finding, and it comes from the regime switch plus the 52-week-high filter, not from
  the breakout entry. That could be tested as a simple rule: hold Stage 1 leaders equal-weight while
  SPY is above its EMA50, cash otherwise, no breakout timing.
- If alpha is wanted: the entry rule needs to be rebuilt and judged from the start on point-in-time
  membership with 2021 and 2023 in the sample. Nothing in the current rule set clears that bar.
- The data assets are real and reusable: 627-name point-in-time daily cache from 2020
  (`research/cache_pit/`), the 2023-24 and 2025-26 5-minute caches, and the membership history.

Not financial advice.

## Addendum (Oct 14): can a better exit fix it?

Full exit grid on the point-in-time universe, 2021-01-04 to 2026-10-09, same entry, ranked fill, regime
switch (`research/exit_grid_pit.py`, `exit_neighbourhood.py`, `exit_robust.py`; logs in `out/`).

- **Tighter stops make it worse, not better.** EMA21 trail with no stop: +62%, PF 1.37. Add a -5% stop:
  +2%, PF 1.04, win rate 35%. A -3% stop with a +6% target: -13%. Every loss-minimising exit turns one
  large loss into several small ones and cuts the winners that needed room.
- **A better exit exists: hold about 25 sessions with a wide (-8% to -12%) stop, no trail.** Across all
  three sizings it beats the EMA21 trail (+92% to +148% vs +52% to +62%) with a smaller drawdown
  (-12% to -16% vs -17% to -38%). Chosen on 2021-23 alone, every top-5 cell beats SPY on 2024-26.
- **But it does not create an edge the entry lacks.** Per-signal 25-session excess over SPY is -0.18%
  for all signals (t = -1.5) and +0.26% for the top-3 ranked signals of each day (t = 1.1): not
  distinguishable from zero. The 10 x 10% result (+148%, 4 of 6 years over SPY, min PF 1.21) is partly
  slot-path luck: the same rules at 5 x 20% or 20 x 5% give +92% to +98% and beat SPY in 2 of 6 years.
- Verdict unchanged. If the engine is built anyway, the exit profile should be hold-25-sessions with a
  -10% stop rather than the EMA21 trail, pre-registered, and judged on paper by the same gates.

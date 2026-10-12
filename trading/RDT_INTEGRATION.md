# Adding the Gajjala momentum swing setup to the RDT engine

Status: design + compatibility backtest. Written without access to `rdt_trading_engine.py`
(repo `SatishKE/IBKR-rdt` is not reachable from this session), against RDT_SYSTEM_OVERVIEW v2.8
and the TAPE-001 study. Everything below about the engine's internals is read from those docs
and must be checked against the code before wiring anything in.

## 1. The question: does the edge survive RDT's gates and exits?

The validated Gajjala rules (`REPORT.md`) enter on the first 5-minute close above the first
15 minutes' high from 09:45, and exit on a 5% stop or the close of the 3rd session. The RDT engine
enters only between 10:00 and 10:30 after the SPY-green / ORB30-or-VWAP / RVOL / candle-path /
fast-MACD chain, and exits on a 1.5x ATR stop with the T1 1.5% / breakeven / T2 / T3 ladder and
day-2, day-3 and day-4 stall and time stops. Dropping the Gajjala signal list into
`rdt_signal_tracker` means the engine trades it under RDT's rules, so I replayed the same signal
set (Stage 1 top 15, within 10% of 52-week high) under all four combinations on Jan 2025 to
Oct 9 2026, 444 sessions, Alpaca SIP data (`research/rdt_compat.py`, `research/out/rdt_compat.log`):

| Entry | Exit | Trades | Win | Avg return / trade | PF (IS 2025 / OOS 2026) | Portfolio, 10 x 10% |
|---|---|---|---|---|---|---|
| Gajjala 09:45 ORB15 | Gajjala 5% stop, 3-session hold | 415 | 54% | +1.41% | 1.79 (1.63 / 1.95) | +67.9%, max DD 5.6% |
| Gajjala 09:45 ORB15 | RDT ladder | 420 | 75% | +0.69% | 1.67 (1.17 / 2.52) | +26.6%, max DD 7.9% |
| RDT gates 10:00-10:30 | Gajjala exits | 92 | 47% | +0.79% | 1.37 (1.03 / 1.78) | n/a |
| RDT gates 10:00-10:30 | RDT ladder ("plain 6th strategy") | 93 | 77% | +0.86% | 2.12 (2.10 / 2.14) | +7.1%, exposure 5% |

RDT's exit approximation: ATR14(daily) x 1.5 stop capped at 8%; T1 +1.5% sells 25% and moves the
stop to entry; T2 +5.5% sells 25%, stop to T1; T3 +10% sells 25%, stop to T2; day-2 EOD cut if no
tier and <= -2.5%; day-3 EOD cut if no T1 and <= -0.5%; day-4 EOD exit if no tier; T1-without-T2
timeout after 4 days; hard cap 8 sessions. RDT's gate approximation: 10:00 <= t < 10:30, SPY above
prior close, close >= 30-min ORB high or >= VWAP, bar volume >= 20-bar average, CLV >= 0.5 on the
09:45/09:50/09:55/10:00 bars, MACD(3,10) line > 0.

What the table says:

- **The RDT exit ladder halves the edge.** 335 of the 420 trades under the ladder ended on a stop,
  most of them the breakeven stop after T1 fired at +1.5%. Momentum leaders routinely pull back to
  entry before the 3-day move happens; the ladder locks in 1.5% on a quarter of the position and
  then gets shaken out of the rest. Per-trade return drops from +1.41% to +0.69%, and the 2025
  half is barely positive (PF 1.17).
- **The RDT gate window throws away 78% of the signals.** Most Gajjala entries fire between 09:45
  and 10:00 (the TAPE-001 entry-clock ladder shows the same decay: 09:35 entries average +1.09%
  to close, 10:30 entries +0.28%). The 10:00 floor and the 4-of-4 candle gate leave 92 trades in
  21 months, about one a week.
- **Plain sixth strategy is high quality but too small to matter.** PF 2.12 and a 77% win rate,
  consistent in both halves, but 93 trades and 5% average exposure: +7% over 21 months on a
  $100k book. It would not hurt the engine; it just would not do much.

So: do not add it as a plain sixth strategy. Add it as a strategy with its own entry window and
its own exit profile. The engine already has the concept of multi-day holds (strategy 5, "RDT
Swing Trade Setup") and per-strategy toggles (`disabled_strategies`), so a per-strategy exit
profile is the natural extension.

## 2. The new strategy row

In the same format as the existing five (six) strategies:

| Strategy | Direction | Rule | Starting confidence |
|---|---|---|---|
| Gajjala Momentum Swing | Long, 3-day hold | Scan (daily, prior close): 21-day return beats SPY, close above SMA50, price above $10, 20-day average dollar volume at least $25M, within 10% of the 52-week high; rank by 21-day return, keep the top 15. Entry (5-min, 09:45 to 15:55): first close above the 09:30-09:44 high, bar volume at least 1.5x the 20-bar average, close > EMA9 > EMA21, close above session VWAP, SPY above its own session VWAP. Exit: 5% hard stop, else sell at the close of the 3rd session after entry. No tiers, no breakeven move, no stall cuts. | 0.65, +0.02 per rank above 10 (rank 1 = 0.83), capped at 0.90 |

Why a rank-scaled confidence: in the backtest, top-10 names had PF 2.03 vs 1.80 for the top 15, and
top-30 fell to 1.44. The rank is the quality signal, so it should feed the 0.75 gate instead of a flat
number. Skip the strategy entirely when SPY is below its EMA50 (not tested in a bear; the SPY-VWAP
gate covers single bad days, not a downtrend).

### Is it new, or the Swing Trade Setup again?

Both want relative strength, a 50-day trend and proximity to the 52-week high, so I measured the overlap
on 444 sessions with the Swing Trade Setup approximated as: 10-day RS vs SPY >= 1pp, close above EMA50,
5-day ATR under 80% of the 20-day, within 10% of the 52-week high (`research/overlap.py`,
`research/out/overlap.log`):

| | Avg names / day | Share of Gajjala names also in it |
|---|---|---|
| Gajjala Stage 1 top 15 | 15.0 | |
| RDT Swing Trade Setup (all qualifying) | 11.3 | 12% |
| RDT Swing Trade Setup top 15 by RS | 11.3 | 10% |

Only about 1 name in 8 appears on both lists. The reason is the volatility filter: the Swing setup wants
contracting ATR (a quiet base), the Gajjala list wants the names that already moved the most in 21 days,
which are rarely quiet. They are different stocks.

They also behave differently. Daily-bar proxy on the same period (buy next open, 5% stop, sell the
3rd close, no intraday filter at all):

| List | Trades | Avg return | PF |
|---|---|---|---|
| Gajjala Stage 1 top 15 | 6,611 | +0.38% | 1.23 |
| Gajjala names not in the Swing setup | 5,825 | +0.41% | 1.24 |
| Gajjala names also in the Swing setup | 786 | +0.14% | 1.10 |
| RDT Swing setup, all qualifying | 5,000 | +0.06% | 1.05 |
| RDT Swing setup, top 15 by RS | 3,454 | +0.01% | 1.01 |

The 3-day drift lives in the high-momentum names the Swing setup excludes. The intraday entry filter
then lifts PF from 1.23 to 1.80 (section 1). So the addition is not a duplicate and should not be merged
into strategy 5; it is a separate long strategy with its own exit profile.

## 3. Proposed integration (to be confirmed against the code)

### 3a. Scanner side (EOD pipeline step 4, `rdt_morning_scanner_alpaca.py`)

Add a sixth strategy, `Gajjala Momentum Swing`, computed from the same Alpaca daily bars the
production scanner already pulls:

- 21-day return > SPY 21-day return
- close > 50-day SMA, close > $10, 20-day average dollar volume > $25M
- within 10% of the 52-week high
- rank by 21-day return, keep the top 15

Write one `rdt_signal_tracker` row per name with `strategy='Gajjala Momentum Swing'`,
`list_type` as the production tag, `confidence` set so it clears the 0.75 gate (the Stage 1 filter
is the quality gate; rank 1 to 15 can map to 0.95 down to 0.80), and the indicators the engine
already stores (rs_score = 21-day return minus SPY, pct_from_52w_high, adv20, atr14_pct). Reuse
`stage1()` from `gajjala_swing_scanner_us.py` as the reference implementation; it is 30 lines.

### 3b. Engine side (`rdt_trading_engine.py`)

Branch on strategy at three points. Everything else (slots, R-sizing, daily-loss halt,
reconcilers, legs, EOD reports, dashboard) stays shared.

1. **Entry gate.** For `Gajjala Momentum Swing` rows, replace the 10:00-10:30 chain with:
   first 5-minute close above the 09:30-09:44 high (the existing `rdt_orb_snapshot.py` already
   stores `orb_high` from the 9:30-9:44 bars, so this is "price > orb_high and previous bar close
   <= orb_high"), bar volume >= 1.5x the 20-bar average, close > EMA9 > EMA21 on 5-minute closes,
   close > session VWAP, SPY above its session VWAP (not prior close), window 09:45 to 15:55.
   Keep the SPY-green gate off for this strategy: in the backtest, SPY-vs-prior-close is a weaker
   filter than SPY-vs-VWAP for this entry (PF 1.56 vs 1.80 when swapped).
2. **Exit profile.** `stop = entry * 0.95` (not ATR), no tiers, no breakeven move, no stall cuts,
   sell the full position at the close of the 3rd session after entry (the engine's existing
   3:45/3:55 EOD exit path can do this with a per-trade `exit_session` date). Carry overnight
   like strategy 5.
3. **Sizing.** Risk-based sizing already handles it: R = $75 at a 5% stop is a $1,500 position.
   If that is too small to be worth the slot, size this strategy at a fixed 10% of the
   `max_deployment_cap` instead (the backtest used 10% of equity, max 10 open).

Suggested config keys (both books, paper first): `gajjala_enabled`, `gajjala_stop_pct=0.05`,
`gajjala_hold_sessions=3`, `gajjala_vol_mult=1.5`, `gajjala_max_off_high=0.10`,
`gajjala_size_mode='risk'|'fixed_pct'`. Add the strategy name to `disabled_strategies` as the
kill-switch, same as Algo Lines.

### 3c. What TAPE-001 already says that agrees

Your own tape study points the same way, which is the main reason to trust the cross-check:

- ORB@9:45 pass is the strongest single condition in the gate audit (+0.90% vs +0.02% to close).
- "% vs VWAP" at 10:00 and 10:30 in the [1, 99) band: +2.4% and +2.7% to close, 76% and 83% win.
- Range position [0.75, 1.0] at 09:45: +0.83% vs -0.77% in the bottom quartile.
- 20-day RS vs SPY >= 12pp held up out-of-sample (+0.10 excess OOS), ATR14% 3-4% held up.
- The entry-clock ladder decays monotonically from 09:31 to 10:30 on every book.

The Gajjala Stage 1 list is essentially "20-day RS >= 12pp, near the 50-day high, high ADV", and
the entry is "ORB@9:45 pass + above VWAP + volume". The one thing it adds that TAPE-001 does not
cover is the 3-session hold with no tier ladder, and that is where the 2x2 says the money is.

## 4. Validation plan before real money

1. Paper book only, `gajjala_enabled=True`, real book off.
2. Run `gajjala_swing_scanner_us.py --date <day>` against the engine's disposition log each night for
   two weeks: every signal it prints should appear as an engine entry (or a logged no-slot).
3. Judge at n >= 60 closed trades or 2026-12-31, whichever first. Success = PF >= 1.3 and the
   3-session exit distribution matching the backtest (about 70% held to exit, 25% stopped).
4. Watch the one known weak spot: Q3 2026 produced only 26 signals and flat equity. If the
   signal count stays below 5 a week for a month, that is the strategy idling, not broken.

## 5. Files

- `research/overlap.py`, `research/out/overlap.log`: overlap with the Swing Trade Setup
- `research/rdt_compat.py`: the 2x2 replay (RDT gate and exit approximations are at the top)
- `research/out/rdt_compat.log`: results; `rdt_compat_A.csv` to `_D.csv`: trade lists per cell
- `gajjala_swing_scanner_us.py`: reference implementation of the Stage 1 filter and the entry check

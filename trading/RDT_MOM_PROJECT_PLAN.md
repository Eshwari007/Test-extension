# rdt_mom: Momentum Swing + Trend Engine — Project Plan and System Logic

Version 1.1 — Oct 13 2026 (revised after the 2023-2024 out-of-sample test). Author: Claude, for Sat (Esh).
Decisions taken: standalone engine in the style of `rdt_trading_engine.py`, own MySQL tables in `stocks_db`,
paper-automated from day one (real book off), macOS LaunchAgent, scope = swing book + trend book.
Earnings collar is Phase 6. Everything here traces back to the research in `REPORT.md`,
`P_EVERPURE_DEEP_DIVE.md`, `EARNINGS_HEDGE_COLLAR.md`, `OOS_2023_2024.md` and `research/`.

## 1. What it does, in one paragraph

Every evening it ranks the S&P 500 + Nasdaq 100 by 21-day return and keeps the top 15 that beat SPY,
sit above their 50-day average, trade $25M+ a day and are within 10% of their 52-week high. The next
day two books trade that list. The **swing book** buys the first 5-minute close above the opening
15-minute high on 1.5x volume (with EMA and VWAP confirmation and SPY above its VWAP), holds three
sessions, 5% stop. The **trend book** buys the next open after a daily close above the 20-day high on
1.5x volume and holds until a daily close below the EMA21, with an 8% disaster stop. Each book has its
own capital, slots and sizing. Everything is written to MySQL so the existing dashboard, EOD reports
and reconcilers can see it.

Backtests, $100k, 5 bps slippage, with the two implementation rules below (ranked slot filling and
the SPY regime switch). 2025 was used to choose the rules; 2026, 2023 and 2024 are out-of-sample
(`research/out/oos_checks_2324.log`, `oos_checks_2526.log`):

| Configuration | 2023-24 (SPY +54%) | 2025-26 (SPY +33%) | Max DD |
|---|---|---|---|
| Trend book only, 10 x 10%, ranked, regime switch | +87% | +57% | -11% / -19% |
| Trend book only, 20 x 5%, ranked | +75% | +64% | -8% / -17% |
| Swing book only, 10 x 10%, regime switch | +11% | +57% | -14% / -5% |
| 50/50 swing + trend, 10 x 10% each, both rules | +41% | +53% | -8% / -10% |
| 50/50 swing + trend, 5 x 20% each, both rules | +70% | +100% | -10% / -11% |

Per-trade edge by year: trend profit factor 1.31 / 2.01 / 1.35 / 1.46 (2023 / 2024 / 2025 / 2026);
swing 1.16 / 1.22 / 1.63 / 1.95. The trend edge is stable; the swing edge depends on the market
having a leading theme. Hence the weighting below.

**Defaults in this plan (v1.1):** trend book 65% of capital, 20 slots x 5%, ranked by Stage 1
relative strength, regime switch on; swing book 35% of capital, 10 slots x 10%, regime switch on.
Never run the trend book at 5 x 20%: concentration was the worst trend configuration in both windows.
All of these are config values in `rdt_mom_config.py`.

## 2. Components

```
rdt_mom/
├── rdt_mom_config.py        all parameters, both books, kill-switches, DB/broker settings
├── rdt_mom_formulas.py      pure functions: Stage 1 filter, indicators, entry checks, exit rules, sizing
│                            (single source of truth, imported by scanner, engine, backtester and tests)
├── rdt_mom_data.py          Alpaca data access: daily bars, 5-min bars, latest trades, trading calendar; caching
├── rdt_mom_scanner.py       nightly Stage 1 -> rdt_mom_signals (one row per leader per session)
├── rdt_mom_engine.py        the always-on service: polls, gates, orders, exits, state, heartbeat
├── rdt_mom_broker.py        Alpaca orders with client_order_id idempotency, fill polling, position sync
├── rdt_mom_db.py            MySQL access layer (SQLAlchemy/pymysql), schema DDL, upserts
├── rdt_mom_reconcile.py     startup + 5-min alert-only reconcile: Alpaca positions vs book
├── rdt_mom_eod.py           end-of-day: mark positions, write rdt_mom_eod_report, email summary
├── rdt_mom_replay.py        offline replay of any date range through the SAME formulas (regression vs research engine)
├── dash_pages/mom.py        Streamlit page: signals, open positions, trades, equity curve, health
├── tests/                   pytest: formulas vs research fixtures, order idempotency, exit state machine
└── launchd/com.rdt.momengine.plist
```

Naming follows the RDT convention (`rdt_*`). Nothing imports from `rdt_trading_engine.py`; the only
shared things are the MySQL server, the Alpaca keys file (`mysql_stocks_alpaca.py`) and the dashboard.

## 3. MySQL schema (new tables, all prefixed `rdt_mom_`)

```sql
rdt_mom_signals        -- Stage 1 output, one row per (session_date, symbol)
  id, session_date, symbol, rank, ret_21d, spy_ret_21d, rs_vs_spy, close, sma50, pct_off_52w_high,
  avg_dollar_vol_20d, eligible (bool: within 10% of high), scan_time, scanner_version

rdt_mom_trades         -- one row per position, both books
  id, book ('swing'|'trend'|'paper'/'real' via account column), account, symbol, signal_id,
  entry_time, entry_px, qty, stop_px, planned_exit_session (swing), status ('open'|'closed'|'failed'),
  exit_time, exit_px, exit_reason ('stop'|'maxhold'|'ema21'|'disaster'|'manual'|'eod_flat'),
  pnl, r_multiple, entry_order_id, exit_order_id, client_order_id, collar_json (phase 4)

rdt_mom_trade_legs     -- every fill event with the indicator snapshot at that minute
  id, trade_id, leg_type ('entry'|'exit'), ts, px, qty, order_id, vwap, ema9, ema21, vol_ratio,
  spy_above_vwap, bar_in_day, notes

rdt_mom_disposition    -- why a signal did or did not trade (mirrors rdt_signal_disposition)
  id, session_date, symbol, book, ts, decision ('entered'|'no_slot'|'already_held'|'gate_fail'|
  'spy_off'|'no_data'|'kill_switch'), gate_json

rdt_mom_eod_report     -- per session per book: equity, cash, open_value, realized, unrealized,
  n_open, n_entries, n_exits, max_dd_to_date, spy_close

rdt_mom_heartbeat      -- ts, loop_ms, last_bar_ts, errors_last_hour, mode
```

Indexes: (session_date, symbol) on signals and disposition; (status, account, book) on trades;
unique (client_order_id) on trades. All timestamps stored in UTC, displayed in ET.

## 4. The algorithms

### 4.1 Stage 1 (nightly, `rdt_mom_scanner.py`), runs ~17:30 ET after the EOD pipeline

```
universe  = S&P 500 ∪ Nasdaq 100 tickers − BLACKLIST           # source: cached CSV, refreshed weekly
bars      = Alpaca daily bars, split-adjusted, 320 calendar days, feed=sip
spy_ret21 = SPY.close[-1] / SPY.close[-22] − 1
for each symbol:
    close      = c[-1]
    ret21      = close / c[-22] − 1
    sma50      = mean(c[-50:])
    dollar_vol = mean(c[-20:] * v[-20:])
    hi52       = max(h[-252:])
    passes     = ret21 > spy_ret21 and close > sma50 and close > 10 and dollar_vol > 25e6
leaders  = top 15 of {passes} by ret21
eligible = leaders where close / hi52 − 1 >= −0.10
write rdt_mom_signals (all 15, eligible flag); email the list (informational)
```

Why these numbers: `REPORT.md` §4 (top-N, 52-week filter, dollar volume) and `round5.log` neighbourhood tests.
Rank is stored because the trend book fills slots by rank (§4.4).

### 4.2 Shared intraday features (`rdt_mom_formulas.py`)

Computed on regular-hours 5-minute bars (09:30 ≤ t < 16:00 ET) per symbol, on every poll:

```
vwap      = cumsum(typical_price * volume) / cumsum(volume), reset each session
ema9      = ewm(close, span=9);  ema21 = ewm(close, span=21)   # continuous across sessions, 5 days of history
avgvol20  = rolling mean of volume over the previous 20 bars (excludes current bar)
orb_high  = max(high of bars 1..3)  (09:30, 09:35, 09:40)
bar_index = position of the bar within the session (0-based)
spy_above_vwap = SPY.close > SPY.vwap on the same bar
```

The engine evaluates only **completed** bars. A bar that started at 09:45 is evaluated at 09:50:00 + 2 s.

### 4.3 Swing book entry (every 5 minutes, 09:50 to 15:55)

```
for symbol in eligible leaders not already held in the swing book today:
    bar = latest completed bar
    fire = bar_index >= 3
       and bar.close > orb_high and prev_bar.close <= orb_high      # first close above the opening range
       and bar.volume >= 1.5 * avgvol20
       and bar.close > ema9 > ema21
       and bar.close > vwap
       and spy_above_vwap
       and 09:45 <= bar.start_time <= 15:55
    if fire and swing_slots_free and SPY above EMA50 (daily):
        qty      = floor(book_equity * SIZE_FRAC / bar.close)          # 10% default
        stop_px  = bar.close * 0.95
        exit_session = 3rd trading session after today (Alpaca calendar)
        submit market buy with client_order_id = f"mom-swing-{account}-{symbol}-{session}-{hhmm}"
        on fill: write trade (status open), submit GTC stop order at stop_px, write entry leg
    else: write disposition row with the gate results
```

### 4.4 Trend book entry (once per day, at 09:31 for the previous day's close signal)

```
at 16:05 ET (after the close) for every eligible leader:
    fire = close > max(high[-21:-1])            # 20-day high, excluding today
       and close > ema50(daily)
       and volume >= 1.5 * mean(volume[-21:-1])
    candidates = fired symbols not held in trend book, sorted by Stage 1 rank (1 first)
next session 09:31 ET:
    for each candidate while trend_slots_free:
        if open price < previous close * 0.97: skip (gap-down into the breakout invalidates it)
        qty = floor(book_equity * SIZE_FRAC / open_px); market buy; stop_px = fill * 0.92 (disaster stop, GTC)
```

Ranking by Stage 1 relative strength is the most important implementation detail in the system: on
2023-24 it lifted the trend book from +35% to +54% before the regime switch (`OOS_2023_2024.md` §3).
First-come filling leaves the best breakouts on the table.

### 4.5 Exits

```
swing (checked every 5 minutes, and at 15:55):
    stop:    GTC stop order at entry*0.95 lives at the broker; engine also checks low <= stop as a backstop
    maxhold: at 15:55 on planned_exit_session -> market sell, reason 'maxhold'
    no targets, no trailing, no breakeven move (REPORT.md §4: all of them reduced returns)

trend (checked once per day at 15:58, and the disaster stop lives at the broker):
    ema21:    if today's close (use 15:58 price as proxy) < EMA21(daily) -> market sell at next open 09:31, reason 'ema21'
              (backtest used next-open fills; selling at 15:58 is an acceptable variant, flag in config)
    disaster: GTC stop at entry*0.92
    max hold: none
```

### 4.6 Sizing, slots, risk (per book)

```
book_equity   = cash + marked value of the book's open positions (never the other book's)
capital split = 65% trend / 35% swing (config; the 50/50 of v1.0 is one line away)
SIZE_FRAC     = 0.05 for the trend book (20 slots), 0.10 for the swing book (10 slots)
MAX_SLOTS     = 1 / SIZE_FRAC
trend book never above 0.10 per slot (5 x 20% was the worst trend configuration in both windows)
one position per symbol per book; a symbol may be in both books at once (they are different trades)
daily loss halt: if book equity falls 3% below the day's starting equity, no new entries that day (exits still run)
regime off-switch: if SPY close < SPY EMA50 at the prior close, no new entries in either book (open positions keep their exit rules).
              Worth +33 points to the trend book in 2023-24 and -3 in 2025-26; it is the only bear-market protection in the system and stays on
kill-switches: file MOM_OFF (both books), MOM_SWING_OFF, MOM_TREND_OFF; checked every loop, no restart needed
```

### 4.7 Order handling (`rdt_mom_broker.py`), ported from the RDT resilience rules

- every submit carries a deterministic `client_order_id`; before any re-send after a timeout or 5xx the
  broker is queried by that id (found → use it; not found → re-send with the same id; lookup failed → hard fail + alert)
- all broker calls wrapped in a 15 s timeout; three consecutive failures → engine goes to `degraded`
  (exits only, alert email), never wedges
- fills: poll `get_order_by_id` up to 60 s; partial fills after 60 s → cancel remainder, book the filled qty
- stop orders are GTC at the broker so a crashed engine still has a stop; on restart the engine re-attaches
  to existing orders by `client_order_id` prefix

### 4.8 Reconciliation

- startup: Alpaca positions vs `rdt_mom_trades` open rows. Adopt nothing automatically; mismatches are
  listed and emailed; a `--adopt` flag books them. Positions from other desks (pmg/pmq/wheel/RDT) are
  identified by their `client_order_id` prefix and ignored.
- every 5 minutes in-session: alert-only compare (same as ENH-RDT-RECON5), one email per symbol per day.
- EOD: match filled SELLs at Alpaca to open trades with no exit (manual closes), book them as `manual`.

### 4.9 Daily timeline (ET)

```
06:30  engine wakes (launchd KeepAlive; caffeinate), loads config, reconciles, reads today's signals
09:30  session open; engine polls 5-min bars from 09:50 (first evaluable bar = 09:45 bar)
09:31  trend book entries for yesterday's breakout candidates (ranked)
09:50 → 15:55 every 5 min  swing entries + swing stop backstop + heartbeat
15:55  swing maxhold exits for positions on their 3rd session
15:58  trend EMA21 check -> queue exits for 09:31 tomorrow (or sell now, per config)
16:05  trend breakout scan for tomorrow; EOD marks; rdt_mom_eod_report; email
17:30  Stage 1 scan for tomorrow -> rdt_mom_signals (after the RDT EOD pipeline so the two don't compete for API quota)
```

## 5. Engine state machine

```
INIT -> RECONCILE -> (PRE_OPEN | IN_SESSION | POST_CLOSE | OVERNIGHT) -> ... ; any -> DEGRADED on broker failure
position: PENDING_ENTRY -> OPEN -> PENDING_EXIT -> CLOSED   (plus FAILED on an unfilled entry)
```
Transitions are logged to `rdt_mom_trade_legs` / `rdt_mom_heartbeat`. A restart at any point recovers from
the DB plus the broker's open orders; there is no in-memory-only state.

## 6. Testing and validation

1. **Formula regression.** `rdt_mom_formulas.py` is tested against fixtures exported from the research
   engine: for 20 symbol-days the signal bars, stops and exits must match `research/out/chosen_trades.csv`
   and `blotter_trend.csv` exactly. This is the test that proves the live code is the backtested code.
2. **Replay mode.** `rdt_mom_replay.py --from 2026-05-01 --to 2026-05-31` runs the engine's own code
   path on historical bars and must reproduce the research P&L within slippage.
3. **Broker tests.** Mocked Alpaca: timeout → lookup → no duplicate order; partial fill; stop re-attach on restart.
4. **Paper validation gates** (judge at the earlier of n ≥ 60 closed trades per book or 2026-12-31):
   trend PF ≥ 1.2 (its four-year floor was 1.31); swing PF ≥ 1.15 (its four-year floor was 1.16) and
   max DD ≤ 10%; both books' trade lists ≥ 90% identical to the replay of the same dates (fill-quality
   check). Failing a gate = stay on paper, investigate. The swing book is also judged on whether it
   adds anything the trend book does not: if its paper Sharpe is below 0.5 after 60 trades, cut its
   weight to 20% rather than switch it off (it still reduces drawdown).
5. **Real money** only after the gates pass, at R-sized reduced capital, with the `MOM_*_OFF` switches tested.

## 7. Phases and effort

| Phase | Deliverable | Effort |
|---|---|---|
| 0. Setup | repo folder, config, Alpaca keys reuse, MySQL DDL, launchd plist skeleton, logging | 0.5 day |
| 1. Scanner + formulas | `rdt_mom_scanner.py`, `rdt_mom_formulas.py`, fixture tests passing | 1.5 days |
| 2. Swing engine | entries, stops, maxhold exits, broker layer, disposition log, heartbeat, reconcile | 3 days |
| 3. Trend book | breakout scan, ranked entries, EMA21 exits, disaster stop, per-book equity | 1.5 days |
| 4. Dashboard + EOD | Streamlit page, EOD report, email, replay tool | 1.5 days |
| 5. Paper run | 1 to 2 weeks of supervised paper trading, daily replay cross-check, bug fixes | ongoing |
| 6. Collar overlay (optional) | earnings calendar feed, `earnings_collar.py` integration for trend positions ≥ 100 shares | 2 days |

About 8 working days of build before the paper run, assuming I can work in the engine repo or a sibling
folder on the Mac. The research engine, scanner and collar tool already written cover roughly a third of
the formula and data code.

## 8. Open questions (answer when convenient; defaults in brackets)

1. Capital per book on paper: [65% trend / 35% swing of whatever the paper account holds; at the $35.8k
   basis that is $23k / $12.5k, which makes the trend slots about $1,150 each (fine for a paper test;
   the collar phase needs 100-share lots and so a larger real book)].
2. Slot sizing: [trend 20 x 5%, swing 10 x 10%]. The 5 x 20% swing setting is the +111% / +70% configuration and remains available for the swing book only.
3. Universe source on the Mac: [Wikipedia S&P 500 + Nasdaq 100 tables, cached weekly, as `rdt_sector_backfill.py` already does].
   Here I used a GitHub mirror because Wikipedia was blocked in the cloud container.
4. Trend exits: sell at 15:58 on the day of the EMA21 break, or at the next open as backtested? [next open].
5. Should the two books share the daily-loss halt and the SPY regime switch with RDT's existing
   1.5% circuit-breaker, or be independent? [independent, own thresholds].
6. Email: reuse `rdt_alerts.py` and the existing SMTP config? [yes].
7. Data feed: SIP on the paper keys works from this container; confirm the Mac's keys have the same entitlement.
8. Name: `rdt_mom` (momentum) or `rdt_gajjala`? [rdt_mom].

## 9. Rebuilding the market data on the Mac

The research cache is 1.8 GB of pickles (794 MB for 2025-26, 973 MB for 2023-24) and is not in git.
Rebuild it with the same script; it needs only the Alpaca keys and about 30 to 45 minutes per window.

```
cd ~/Desktop && git clone --branch claude/exciting-fermi-rt9kny https://github.com/Eshwari007/Test-extension.git
cd Test-extension/trading
python3 -m pip install pandas numpy requests matplotlib openpyxl
export APCA_API_KEY_ID=...  APCA_API_SECRET_KEY=...        # the paper keys from mysql_stocks_alpaca.py work

# 2025-26 window (default settings in research/data.py)
python3 research/data.py                                   # -> research/cache/ (daily.pkl, leaders.pkl, spy5.pkl, intra/<SYM>.pkl)

# 2023-24 window
MOM_CACHE=$PWD/research/cache_2324 MOM_DAILY_START=2022-01-01 MOM_BT_START=2023-01-03 MOM_BT_END=2024-12-31 \
  python3 research/data.py

# any other window, e.g. 2021-22 (bear market; survivorship bias grows the further back you go)
MOM_CACHE=$PWD/research/cache_2122 MOM_DAILY_START=2020-01-01 MOM_BT_START=2021-01-04 MOM_BT_END=2022-12-30 \
  python3 research/data.py
```

What `data.py` does, in order: (1) daily bars for the 516-name universe from `MOM_DAILY_START`,
split-adjusted, SIP feed; (2) Stage 1 top-30 leaders for every session in the window → `leaders.pkl`;
(3) 5-minute bars for every leader over the dates it was on the list, plus SPY → `intra/`. It is
resumable: rerunning skips what is already cached. Rate limit is 200 requests a minute; the script
backs off on 429s.

Then the studies run against the cache: `python3 research/run.py` (baseline, sensitivity, grid),
`round2.py` to `round5.py`, `combined_100k.py`, `replay_trades.py` (writes the blotter), and for the
2023-24 cache `python3 research/oos_2324.py` and `python3 research/oos_checks.py 2324`. Every result
quoted in the reports is reproducible from these.

The universe file `data/sp500.csv` is a GitHub mirror of the Wikipedia S&P 500 table (Wikipedia was
blocked from the cloud container). On the Mac, `rdt_sector_backfill.py` already pulls the live table;
reuse that and add the 13 Nasdaq-100 names listed in `gajjala_scanner_us.py`.

## 10. What exists already (reuse)

- `research/data.py`: the data builder (section 9)
- `gajjala_swing_scanner_us.py`: Stage 1 + swing entry check, tested against the research engine on two sessions → becomes `rdt_mom_scanner.py` + half of `rdt_mom_formulas.py`
- `research/engine.py`: the vectorised backtester → the oracle for the formula regression tests and `rdt_mom_replay.py`
- `research/capture_universe.py`: the trend entry/exit logic → `rdt_mom_formulas.py` trend functions
- `earnings_collar.py`: Phase 6
- `research/out/*.csv`: fixtures

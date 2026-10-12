#!/usr/bin/env python3
"""Gajjala Momentum Swing Scanner (US) - the version that survived the backtest.

What changed vs the original PDF rules and why (see REPORT.md):
  * Entry: break of the first 15 minutes' high (opening range) on volume >= 1.5x the 20-bar
    average, with close > EMA9 > EMA21, close > session VWAP and SPY above its own VWAP.
    The original 6-bar bull-flag breakout lost money in every tested variant over 21 months.
  * Universe: Stage 1 leaders (top 15 by 21-day return, beating SPY, above 50 SMA, price > $10,
    $25M+/day) AND within 10% of the 52-week high.
  * Exit: 5% hard stop, otherwise sell at the close of the 3rd session after entry.
    No profit targets, no EMA9 trail (both reduced returns in testing).
  * Sizing: 10% of equity per position, at most 10 open positions (so 0.5% of equity at risk
    per trade at the stop, same as the original).

Usage
  python gajjala_swing_scanner_us.py                 # scan now (run every 5 min, 09:45-16:00 ET)
  python gajjala_swing_scanner_us.py --date 2026-05-05   # replay a past session, print all signals
  python gajjala_swing_scanner_us.py --manage        # list open positions due for exit today
  python gajjala_swing_scanner_us.py --paper         # also submit paper orders (off by default)

Auth: set APCA_API_KEY_ID / APCA_API_SECRET_KEY, or run behind a proxy that injects them.
Data: Alpaca SIP feed (set FEED=iex if your plan has no SIP access; volume checks get noisier).
"""
import os, sys, json, math, time, argparse, datetime as dt
from zoneinfo import ZoneInfo
import requests
import pandas as pd
import numpy as np

# ---------------- settings ----------------
FEED = os.environ.get("FEED", "sip")
DATA_URL = "https://data.alpaca.markets/v2/stocks/bars"
TRADE_URL = os.environ.get("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
HERE = os.path.dirname(os.path.abspath(__file__))
SP500_CSV = os.path.join(HERE, "data", "sp500.csv")
STATE_FILE = os.path.join(HERE, "swing_positions.json")
SIGNALS_CSV = os.path.join(HERE, "us_swing_signals.csv")
LEADERS_CSV = os.path.join(HERE, "us_swing_leaders.csv")

# Stage 1 (daily)
LOOKBACK_1M = 21
TOP_N = 15
MIN_PRICE = 10.0
MIN_DOLLAR_VOL = 25_000_000
MAX_OFF_HIGH_PCT = 10.0      # within 10% of 52-week high
BLACKLIST = {"MP"}
NDX_EXTRA = ["SHOP", "ARM", "MSTR", "MELI", "PDD", "ASML", "AZN", "TEAM", "ZS", "CCEP", "GFS", "TTD", "CRWV"]
# Stage 2 (5-min)
ORB_BARS = 3                 # opening range = first 15 minutes
VOL_MULT = 1.5
EARLIEST = dt.time(9, 45)    # first bar that can signal (bar start time)
LATEST = dt.time(15, 55)
# Exits and sizing
STOP_PCT = 5.0
HOLD_SESSIONS = 3            # sell at the close of the 3rd session after entry
SIZE_FRAC = 0.10
MAX_POSITIONS = 10
ET = ZoneInfo("America/New_York")

sess = requests.Session()
_h = {}
if os.environ.get("APCA_API_KEY_ID"):
    _h = {"APCA-API-KEY-ID": os.environ["APCA_API_KEY_ID"], "APCA-API-SECRET-KEY": os.environ["APCA_API_SECRET_KEY"]}
sess.headers.update(_h)


# ---------------- data ----------------
def get_bars(symbols, timeframe, start, end=None):
    out = {s: [] for s in symbols}
    for i in range(0, len(symbols), 200):
        params = {"symbols": ",".join(symbols[i:i + 200]), "timeframe": timeframe, "start": start,
                  "limit": 10000, "feed": FEED, "adjustment": "split", "sort": "asc"}
        if end:
            params["end"] = end
        token = None
        while True:
            if token:
                params["page_token"] = token
            for attempt in range(6):
                r = sess.get(DATA_URL, params=params, timeout=60)
                if r.status_code == 429:
                    time.sleep(2 ** attempt); continue
                r.raise_for_status(); break
            js = r.json()
            for s, bars in (js.get("bars") or {}).items():
                out[s].extend(bars)
            token = js.get("next_page_token")
            if not token:
                break
    frames = {}
    for s, bars in out.items():
        if bars:
            df = pd.DataFrame(bars)
            df["t"] = pd.to_datetime(df["t"], utc=True)
            frames[s] = df.set_index("t").sort_index()[["o", "h", "l", "c", "v"]].astype(float)
    return frames


def universe():
    sp = pd.read_csv(SP500_CSV)
    return sorted((set(sp["Symbol"]) | set(NDX_EXTRA)) - BLACKLIST)


def utc_iso(d, t=dt.time(0)):
    return dt.datetime.combine(d, t, ET).astimezone(dt.timezone.utc).isoformat()


# ---------------- stage 1 ----------------
def stage1(daily, spy, asof):
    """Leaders using daily bars up to and including `asof` (previous session's close)."""
    sp = spy[spy.index.tz_convert(ET).date <= asof]["c"]
    spy_ret = sp.iloc[-1] / sp.iloc[-LOOKBACK_1M - 1] - 1
    rows = []
    for sym, df in daily.items():
        d = df[df.index.tz_convert(ET).date <= asof]
        if len(d) < 60:
            continue
        c = d["c"]; close = c.iloc[-1]
        ret1m = close / c.iloc[-LOOKBACK_1M - 1] - 1
        sma50 = c.iloc[-50:].mean()
        dvol = (d["c"] * d["v"]).iloc[-20:].mean()
        hi52 = d["h"].iloc[-252:].max()
        off_high = (close / hi52 - 1) * 100
        if ret1m > spy_ret and close > sma50 and close > MIN_PRICE and dvol > MIN_DOLLAR_VOL:
            rows.append(dict(symbol=sym, close=close, ret_1m=ret1m, rs_vs_spy=ret1m - spy_ret,
                             pct_off_52w_high=off_high, avg_dollar_vol=dvol))
    L = pd.DataFrame(rows).sort_values("ret_1m", ascending=False).head(TOP_N)
    L["rank"] = range(1, len(L) + 1)
    L["within_10pct_high"] = L.pct_off_52w_high >= -MAX_OFF_HIGH_PCT
    L["asof"] = asof
    return L, spy_ret


# ---------------- stage 2 ----------------
def features(df):
    df = df.copy(); df.index = df.index.tz_convert(ET)
    t = df.index.time
    df = df[(t >= dt.time(9, 30)) & (t < dt.time(16, 0))]
    df["date"] = df.index.date
    g = df.groupby("date")
    tp = (df["h"] + df["l"] + df["c"]) / 3
    df["vwap"] = (tp * df["v"]).groupby(df["date"]).cumsum() / g["v"].cumsum()
    df["ema9"] = df["c"].ewm(span=9, adjust=False).mean()
    df["ema21"] = df["c"].ewm(span=21, adjust=False).mean()
    df["avgvol20"] = df["v"].shift(1).rolling(20).mean()
    df["bar"] = g.cumcount()
    df["orb_hi"] = g["h"].transform(lambda x: x.iloc[:ORB_BARS].max())
    df["orb_lo"] = g["l"].transform(lambda x: x.iloc[:ORB_BARS].min())
    df["prev_c"] = df["c"].shift(1)
    return df


def check_bar(row, spy_above):
    return {
        "orb_breakout": row.bar >= ORB_BARS and row.c > row.orb_hi and row.prev_c <= row.orb_hi,
        "volume": row.v >= VOL_MULT * row.avgvol20 if not np.isnan(row.avgvol20) else False,
        "ema_stack": row.c > row.ema9 > row.ema21,
        "above_vwap": row.c > row.vwap,
        "spy_above_vwap": bool(spy_above),
        "time_window": EARLIEST <= row.Index.time() <= LATEST,
    }


def scan_session(day, daily, spy, equity, all_bars=False):
    """Return (leaders, signals) for `day`. all_bars=True evaluates every bar (replay); else only the latest."""
    sessions = sorted(set(spy.index.tz_convert(ET).date))
    prev = [d for d in sessions if d < day][-1]
    L, spy_ret = stage1(daily, spy, prev)
    cands = list(L[L.within_10pct_high].symbol)
    intra = get_bars(cands + ["SPY"], "5Min", utc_iso(day - dt.timedelta(days=5)), utc_iso(day, dt.time(23, 59)))
    spy5 = features(intra.pop("SPY")); spy_above = spy5["c"] > spy5["vwap"]
    signals = []
    for s in cands:
        if s not in intra:
            continue
        f = features(intra[s]); f = f[f["date"] == day]
        if f.empty:
            continue
        rows = f.itertuples() if all_bars else [next(f.tail(1).itertuples())]
        for row in rows:
            chk = check_bar(row, spy_above.get(row.Index, False))
            if all(chk.values()):
                entry = row.c; stop = entry * (1 - STOP_PCT / 100)
                qty = math.floor(equity * SIZE_FRAC / entry)
                exit_day = trading_sessions_after(day)[HOLD_SESSIONS - 1]
                signals.append(dict(session=day, time=row.Index.strftime("%H:%M"), symbol=s, entry=round(entry, 2),
                                    stop=round(stop, 2), qty=qty, exit_session=exit_day, orb_high=round(row.orb_hi, 2),
                                    vol_ratio=round(row.v / row.avgvol20, 2), day_gain_pct=round((row.c / f["o"].iloc[0] - 1) * 100, 2),
                                    rank=int(L.set_index("symbol").loc[s, "rank"]), ret_1m=round(float(L.set_index("symbol").loc[s, "ret_1m"]) * 100, 1)))
                if not all_bars:
                    break
            elif not all_bars:
                signals.append(dict(session=day, time=row.Index.strftime("%H:%M"), symbol=s, entry=None, **{"chk_" + k: v for k, v in chk.items()}))
    return L, pd.DataFrame(signals)


# ---------------- state / orders ----------------
def load_state():
    return json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {"positions": []}


def save_state(st):
    json.dump(st, open(STATE_FILE, "w"), indent=2, default=str)


def trading_sessions_after(day, n=HOLD_SESSIONS):
    """Trading days after `day` from the Alpaca calendar (falls back to weekdays)."""
    try:
        r = sess.get(f"{TRADE_URL}/v2/calendar", params={"start": (day + dt.timedelta(days=1)).isoformat(),
                                                           "end": (day + dt.timedelta(days=20)).isoformat()}, timeout=30)
        r.raise_for_status()
        days = [dt.date.fromisoformat(x["date"]) for x in r.json()]
    except Exception as e:
        print("calendar lookup failed, assuming weekdays:", e)
        days = [day + dt.timedelta(days=k) for k in range(1, 30) if (day + dt.timedelta(days=k)).weekday() < 5]
    return days[:n]


def account_equity():
    try:
        r = sess.get(f"{TRADE_URL}/v2/account", timeout=30); r.raise_for_status()
        return float(r.json()["equity"])
    except Exception as e:
        print("could not read account equity, using 100000:", e)
        return 100_000.0


def submit(symbol, qty, side, stop=None):
    """Market order; for buys attach a stop-loss (OTO order class)."""
    o = {"symbol": symbol, "qty": str(qty), "side": side, "type": "market", "time_in_force": "day"}
    if side == "buy" and stop:
        o.update({"order_class": "oto", "stop_loss": {"stop_price": f"{stop:.2f}"}, "time_in_force": "gtc"})
    r = sess.post(f"{TRADE_URL}/v2/orders", json=o, timeout=30)
    print("order", side, symbol, qty, r.status_code, r.text[:200])
    return r.ok


# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="replay a past session (YYYY-MM-DD): prints every signal that day")
    ap.add_argument("--manage", action="store_true", help="list/close positions whose hold has expired")
    ap.add_argument("--paper", action="store_true", help="submit orders to the Alpaca paper account")
    a = ap.parse_args()
    today = dt.datetime.now(ET).date()
    day = dt.date.fromisoformat(a.date) if a.date else today
    equity = account_equity()
    daily = get_bars(universe() + ["SPY"], "1Day", (day - dt.timedelta(days=400)).isoformat(), utc_iso(day, dt.time(23, 59)))
    spy = daily.pop("SPY")
    st = load_state()

    if a.manage:
        due = [p for p in st["positions"] if p["exit_session"] and dt.date.fromisoformat(str(p["exit_session"])) <= day]
        print(f"{len(st['positions'])} open positions; {len(due)} due for exit at the close today:")
        for p in due:
            print(f"  SELL {p['symbol']} x{p['qty']} (entered {p['session']} @ {p['entry']}, stop {p['stop']})")
            if a.paper and submit(p["symbol"], p["qty"], "sell"):
                st["positions"].remove(p)
        save_state(st)
        return

    L, sig = scan_session(day, daily, spy, equity, all_bars=bool(a.date))
    print(f"\nStage 1 leaders as of {L["asof"].iloc[0]} close (* = within {MAX_OFF_HIGH_PCT:.0f}% of 52w high -> eligible):")
    for r in L.itertuples():
        print(f"  {r.rank:2d} {'*' if r.within_10pct_high else ' '} {r.symbol:6s} {r.close:9.2f}  1m {r.ret_1m*100:+6.1f}%  vs SPY {r.rs_vs_spy*100:+6.1f}%  off high {r.pct_off_52w_high:+6.1f}%  $vol {r.avg_dollar_vol/1e6:,.0f}M")
    L.to_csv(LEADERS_CSV, index=False)
    if sig.empty:
        print("\nNo bars to evaluate (market closed or no eligible leaders)."); return
    fired = sig[sig.entry.notna()] if "entry" in sig else sig.iloc[0:0]
    if a.date:
        print(f"\nSignals on {day} ({len(fired)}):")
        print(fired.to_string(index=False) if not fired.empty else "  none")
        return
    print(f"\nLatest bar check ({sig.time.iloc[0]} ET):")
    cols = [c for c in sig.columns if c.startswith("chk_")]
    if cols:
        print(sig[sig.entry.isna()][["symbol"] + cols].to_string(index=False))
    if fired.empty:
        print("\nNo new signals this bar."); return
    held = {p["symbol"] for p in st["positions"]}
    print(f"\nNEW SIGNALS ({len(fired)}):")
    for r in fired.itertuples():
        if r.symbol in held:
            print(f"  {r.symbol}: already held, skip"); continue
        if len(st["positions"]) >= MAX_POSITIONS:
            print(f"  {r.symbol}: max positions reached, skip"); continue
        print(f"  BUY {r.symbol} x{r.qty} @ ~{r.entry}  stop {r.stop}  sell at close of {r.exit_session}  (vol {r.vol_ratio}x, day {r.day_gain_pct:+.1f}%)")
        ok = submit(r.symbol, r.qty, "buy", r.stop) if a.paper else True
        if ok:
            st["positions"].append(dict(symbol=r.symbol, qty=r.qty, entry=r.entry, stop=r.stop, session=str(day),
                                        time=r.time, exit_session=str(r.exit_session)))
            held.add(r.symbol)
    save_state(st)
    hdr = not os.path.exists(SIGNALS_CSV)
    fired.to_csv(SIGNALS_CSV, mode="a", header=hdr, index=False)


if __name__ == "__main__":
    main()

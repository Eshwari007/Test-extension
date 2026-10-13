#!/usr/bin/env python3
"""Earnings shock hedge for a long momentum position: price and (optionally) place a collar on Alpaca.

Structures (all per 100 shares):
  collar       : buy put ~PUT_PCT below spot, sell call ~CALL_PCT above spot, same expiry
  spread-collar: collar plus sell a second put ~FAR_PUT_PCT below (cheaper; protection stops there)
  put          : protective put only (expensive at 60-80% IV; shown for comparison)
Expiry: the first listed expiration on or after the earnings reaction date (P has monthlies only).

Usage
  python earnings_collar.py P --shares 100 --earnings 2026-11-18
  python earnings_collar.py P --shares 100 --earnings 2026-11-18 --put-pct 0.10 --call-pct 0.15
  python earnings_collar.py P --shares 100 --earnings 2026-11-18 --paper      # submit the collar as a 2-leg order
  python earnings_collar.py P --unwind --paper                                 # close open P option legs (after the report)

Auth: APCA_API_KEY_ID / APCA_API_SECRET_KEY, or a proxy that injects them. Paper endpoint by default.
Positions under 100 shares cannot be collared 1:1; the script says so and recommends the exit-before-earnings rule.
"""
import os, sys, math, argparse, datetime as dt, json
import requests
import pandas as pd

DATA = "https://data.alpaca.markets"
TRADE = os.environ.get("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")
S = requests.Session()
if os.environ.get("APCA_API_KEY_ID"):
    S.headers.update({"APCA-API-KEY-ID": os.environ["APCA_API_KEY_ID"], "APCA-API-SECRET-KEY": os.environ["APCA_API_SECRET_KEY"]})


def spot_price(sym):
    return float(S.get(f"{DATA}/v2/stocks/trades/latest", params={"symbols": sym, "feed": "sip"}).json()["trades"][sym]["p"])


def expirations(sym, after):
    js = S.get(f"{TRADE}/v2/options/contracts", params={"underlying_symbols": sym, "expiration_date_gte": after.isoformat(),
                                                          "expiration_date_lte": (after + dt.timedelta(days=120)).isoformat(), "limit": 1000}).json()
    return sorted({c["expiration_date"] for c in js.get("option_contracts", [])})


def chain(sym, exp):
    rows, tok = [], None
    while True:
        p = {"feed": "indicative", "limit": 250, "expiration_date": exp}
        if tok:
            p["page_token"] = tok
        js = S.get(f"{DATA}/v1beta1/options/snapshots/{sym}", params=p).json()
        for osym, sn in js.get("snapshots", {}).items():
            q = sn.get("latestQuote") or {}
            rows.append(dict(sym=osym, type=osym[-9], strike=int(osym[-8:]) / 1000, bid=q.get("bp"), ask=q.get("ap"),
                             iv=sn.get("impliedVolatility"), delta=(sn.get("greeks") or {}).get("delta")))
        tok = js.get("next_page_token")
        if not tok:
            break
    return pd.DataFrame(rows)


def nearest(df, target):
    return df.iloc[(df.strike - target).abs().argsort()[:1]].iloc[0]


def submit_mleg(legs, qty, limit=None):
    """legs: list of (option_symbol, side). Alpaca multi-leg order (order_class=mleg)."""
    o = {"order_class": "mleg", "qty": str(qty), "type": "limit" if limit is not None else "market", "time_in_force": "day",
         "legs": [{"symbol": s, "ratio_qty": "1", "side": side, "position_intent": "buy_to_open" if side == "buy" else "sell_to_open"} for s, side in legs]}
    if limit is not None:
        o["limit_price"] = f"{limit:.2f}"
    r = S.post(f"{TRADE}/v2/orders", json=o, timeout=30)
    print("order:", r.status_code, r.text[:300])
    return r.ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol"); ap.add_argument("--shares", type=int, default=100); ap.add_argument("--earnings", help="YYYY-MM-DD of the reaction session")
    ap.add_argument("--put-pct", type=float, default=0.10); ap.add_argument("--call-pct", type=float, default=0.15); ap.add_argument("--far-put-pct", type=float, default=0.25)
    ap.add_argument("--paper", action="store_true"); ap.add_argument("--unwind", action="store_true")
    a = ap.parse_args()
    sym = a.symbol.upper()
    if a.unwind:
        pos = S.get(f"{TRADE}/v2/positions").json()
        legs = [p for p in pos if p.get("asset_class") == "us_option" and p["symbol"].startswith(sym)]
        print(f"{len(legs)} open {sym} option legs:")
        for p in legs:
            print(f"  {p['symbol']} qty {p['qty']} mkt ${float(p['market_value']):,.0f} P&L ${float(p['unrealized_pl']):,.0f}")
            if a.paper:
                r = S.delete(f"{TRADE}/v2/positions/{p['symbol']}"); print("   close:", r.status_code, r.text[:120])
        return
    if not a.earnings:
        sys.exit("--earnings YYYY-MM-DD required")
    ed = dt.date.fromisoformat(a.earnings)
    spot = spot_price(sym)
    lots = a.shares // 100
    exps = expirations(sym, ed)
    if not exps:
        sys.exit(f"no expirations on/after {ed} for {sym}")
    exp = exps[0]
    ch = chain(sym, exp)
    puts = ch[(ch.type == "P") & ch.ask.notna()]; calls = ch[(ch.type == "C") & ch.bid.notna()]
    pk = nearest(puts, spot * (1 - a.put_pct)); ck = nearest(calls, spot * (1 + a.call_pct)); fk = nearest(puts, spot * (1 - a.far_put_pct))
    days = (dt.date.fromisoformat(exp) - dt.date.today()).days
    pos_val = spot * a.shares
    print(f"{sym} spot {spot:.2f}, {a.shares} shares = ${pos_val:,.0f}; earnings {ed}; first expiry after: {exp} ({days} days); IV ~{pk.iv:.0%}" if pk.iv else f"{sym} spot {spot:.2f}; expiry {exp}")
    if lots == 0:
        print(f"\nPosition is under 100 shares: a 1-lot collar would hedge {100/a.shares:.1f}x the position.")
        print("Recommendation: exit at the close before the report (or cut to half) and re-enter on the post-earnings breakout.")
        print("Alternative for small accounts: replace the shares with one call (delta ~0.35-0.45) into the report; max loss = premium.")
    print(f"\nQuotes ({exp}):")
    print(f"  put  {pk.strike:.0f} ({pk.strike/spot-1:+.0%})  bid {pk.bid} ask {pk.ask}  delta {pk.delta}")
    print(f"  call {ck.strike:.0f} ({ck.strike/spot-1:+.0%})  bid {ck.bid} ask {ck.ask}  delta {ck.delta}")
    print(f"  far put {fk.strike:.0f} ({fk.strike/spot-1:+.0%})  bid {fk.bid} ask {fk.ask}")
    collar = pk.ask - ck.bid; spread_collar = pk.ask - ck.bid - fk.bid; put_only = pk.ask
    print("\nPer 100 shares (buy at ask, sell at bid):")
    for name, cost, floor, cap in (("collar", collar, pk.strike, ck.strike), ("spread-collar (protection ends at far put)", spread_collar, pk.strike, ck.strike), ("protective put", put_only, pk.strike, None)):
        floor_pct = (floor - spot) / spot - cost / spot
        cap_s = f"cap {(cap - spot)/spot - cost/spot:+.1%}" if cap else "no cap"
        print(f"  {name:44s} cost ${cost*100:+,.0f} ({cost/spot:+.2%} of position)  worst case to expiry {floor_pct:+.1%}  {cap_s}")
    print(f"\nScenario at expiry (stock move -> hedged P&L on {a.shares} shares, collar):")
    for mv in (-0.30, -0.20, -0.15, -0.10, -0.05, 0, 0.05, 0.10, 0.15, 0.20, 0.30):
        px = spot * (1 + mv)
        stock = (px - spot) * a.shares
        hedge = (max(pk.strike - px, 0) - max(px - ck.strike, 0) - collar) * 100 * max(lots, 1)
        print(f"  {mv:+5.0%}: unhedged ${stock:+,.0f}   collar ${stock + hedge:+,.0f}")
    if a.paper and lots > 0:
        mid = round((collar - 0.05 * abs(collar)), 2)
        print(f"\nSubmitting {lots} collar(s): buy {pk.sym}, sell {ck.sym}, limit net debit {mid:+.2f}")
        submit_mleg([(pk.sym, "buy"), (ck.sym, "sell")], lots, limit=mid)
        json.dump(dict(symbol=sym, expiry=exp, put=pk.sym, call=ck.sym, lots=lots, placed=str(dt.datetime.now())), open(f"collar_{sym}.json", "w"), indent=2)


if __name__ == "__main__":
    main()

"""Price protective puts and collars on P from the live Alpaca chain (Nov 20 2026 and Jan 15 2027 expiries)."""
import requests, json, math, datetime as dt, numpy as np, pandas as pd
S = requests.Session()
spot = float(S.get("https://data.alpaca.markets/v2/stocks/trades/latest?symbols=P&feed=sip").json()["trades"]["P"]["p"])
print(f"P last trade {spot:.2f}  ({dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC)")
def chain(exp):
    rows=[]; tok=None
    while True:
        p={"feed":"indicative","limit":250,"expiration_date":exp}
        if tok: p["page_token"]=tok
        js=S.get("https://data.alpaca.markets/v1beta1/options/snapshots/P",params=p).json()
        for sym,sn in js.get("snapshots",{}).items():
            q=sn.get("latestQuote",{}); g=sn.get("greeks",{}) or {}
            typ="C" if sym[-9]=="C" else "P"; k=int(sym[-8:])/1000
            rows.append(dict(sym=sym,type=typ,strike=k,bid=q.get("bp"),ask=q.get("ap"),mid=(q.get("bp",0)+q.get("ap",0))/2 if q else None,iv=sn.get("impliedVolatility"),delta=g.get("delta")))
        tok=js.get("next_page_token")
        if not tok: break
    return pd.DataFrame(rows).sort_values(["type","strike"])
for exp,label in (("2026-11-20","Nov 20 2026 (covers Nov 18 earnings, 38 days)"),("2027-01-15","Jan 15 2027 (94 days)")):
    ch=chain(exp); print(f"\n=== {label}: {len(ch)} contracts ===")
    puts=ch[(ch.type=="P")&(ch.strike.between(spot*0.75,spot*1.02))]; calls=ch[(ch.type=="C")&(ch.strike.between(spot*0.98,spot*1.35))]
    print("puts (strike, bid/ask, mid, % of spot, IV, delta):")
    for r in puts.itertuples(): print(f"  {r.strike:7.1f} ({r.strike/spot-1:+5.1%})  {r.bid}/{r.ask}  mid {r.mid:.2f} = {r.mid/spot*100:.2f}% of spot  IV {r.iv if r.iv is None else round(r.iv,2)}  d {r.delta if r.delta is None else round(r.delta,2)}")
    print("calls:")
    for r in calls.itertuples(): print(f"  {r.strike:7.1f} ({r.strike/spot-1:+5.1%})  {r.bid}/{r.ask}  mid {r.mid:.2f} = {r.mid/spot*100:.2f}% of spot  IV {r.iv if r.iv is None else round(r.iv,2)}  d {r.delta if r.delta is None else round(r.delta,2)}")
    # collar menu: buy put at ask, sell call at bid (conservative)
    print("\n  collar menu (buy put at ask, sell call at bid), per 100 shares, for a $%.0f position:" % (spot*100))
    for pk_pct in (0.90,0.95):
        pk=puts.iloc[(puts.strike-spot*pk_pct).abs().argsort()[:1]]
        if pk.empty: continue
        pk=pk.iloc[0]
        for ck_pct in (1.10,1.15,1.20,1.30):
            ck=calls.iloc[(calls.strike-spot*ck_pct).abs().argsort()[:1]]
            if ck.empty: continue
            ck=ck.iloc[0]
            net=(pk.ask or 0)-(ck.bid or 0)
            print(f"    put {pk.strike:.0f} ({pk.strike/spot-1:+.0%}) @ {pk.ask} / call {ck.strike:.0f} ({ck.strike/spot-1:+.0%}) @ {ck.bid}: net cost {net:+.2f} = {net/spot*100:+.2f}% of position; max loss to expiry {(pk.strike-spot)/spot*100-net/spot*100:+.1f}%, max gain {(ck.strike-spot)/spot*100-net/spot*100:+.1f}%")
        print(f"    put {pk.strike:.0f} alone @ {pk.ask}: {pk.ask/spot*100:.2f}% of position")
    ch.to_csv(f"out/P_chain_{exp}.csv",index=False)

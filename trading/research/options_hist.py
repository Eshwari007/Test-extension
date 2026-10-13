"""What would a put or collar have cost and paid on P's three earnings shocks? Real Alpaca option bars."""
import sys, requests, datetime as dt, numpy as np, pandas as pd; sys.path.insert(0,'.')
import data as D
S=requests.Session(); ET=D.g.ET
P=D.load("daily.pkl")["P"].copy(); P.index=P.index.tz_convert(ET).date
def bars(syms,start,end):
    out={}
    for i in range(0,len(syms),100):
        js=S.get("https://data.alpaca.markets/v1beta1/options/bars",params={"symbols":",".join(syms[i:i+100]),"timeframe":"1Day","start":start,"end":end,"limit":10000}).json()
        for s,b in js.get("bars",{}).items(): out[s]=pd.DataFrame(b).assign(t=lambda d: pd.to_datetime(d.t).dt.date).set_index("t")
    return out
events=[("Q3 FY26",dt.date(2025,12,3),["PSTG251205","PSTG251219"]),("Q1 FY27",dt.date(2026,5,28),["P260529","P260605","P260618"]),("Q2 FY27",dt.date(2026,8,27),["P260828","P260904","P260918"])]
sessions=list(P.index); rows=[]
for name,react,roots in events:
    i=sessions.index(react); setup=sessions[i-5]; spot=P.c.loc[setup]; after=P.c.loc[react]; after_o=P.o.loc[react]
    print(f"\n=== {name}: reaction day {react}; hedge set up at close {setup} with P={spot:.2f}; reaction close {after:.2f} ({after/spot-1:+.1%}), open {after_o:.2f} ===")
    grid=[round(x*2)/2 for x in np.arange(spot*0.75,spot*1.35,2.5)]
    for root in roots:
        syms=[f"{root}P{int(k*1000):08d}" for k in grid]+[f"{root}C{int(k*1000):08d}" for k in grid]
        B=bars(syms,(setup-dt.timedelta(days=3)).isoformat(),(react+dt.timedelta(days=2)).isoformat())
        if not B: print(f"  {root}: no data"); continue
        def px(sym,d):
            b=B.get(sym)
            if b is None: return None
            b2=b[b.index<=d]
            return float(b2.c.iloc[-1]) if len(b2) else None
        print(f"  expiry root {root}: {len(B)} contracts with data")
        tab=[]
        for k in grid:
            ps=f"{root}P{int(k*1000):08d}"; cs=f"{root}C{int(k*1000):08d}"
            p0,p1,c0,c1=px(ps,setup),px(ps,react),px(cs,setup),px(cs,react)
            if p0 or c0: tab.append(dict(strike=k,pct=k/spot-1,put_setup=p0,put_react=p1,call_setup=c0,call_react=c1))
        T=pd.DataFrame(tab); print(T.round(2).to_string(index=False))
        # hedge economics: 100 shares
        unh=(after-spot)*100
        for pk_pct in (0.90,0.95):
            pr=T[T.put_setup.notna()]; 
            if pr.empty: continue
            pk=pr.iloc[(pr.strike-spot*pk_pct).abs().argsort()[:1]].iloc[0]
            put_cost=pk.put_setup*100; put_val=(pk.put_react if pd.notna(pk.put_react) else max(pk.strike-after,0))*100
            hedged=unh-put_cost+put_val
            line=f"  put {pk.strike:.1f} ({pk.pct:+.0%}) cost ${put_cost:,.0f} ({put_cost/(spot*100):.1%} of position) -> worth ${put_val:,.0f} after: unhedged {unh:+,.0f}  hedged {hedged:+,.0f}  ({hedged/(spot*100):+.1%} vs {unh/(spot*100):+.1%})"
            cr=T[T.call_setup.notna()&(T.strike>spot*1.05)]
            if not cr.empty:
                ck=cr.iloc[(cr.strike-spot*1.12).abs().argsort()[:1]].iloc[0]
                call_prem=ck.call_setup*100; call_val=(ck.call_react if pd.notna(ck.call_react) else max(after-ck.strike,0))*100
                line+=f" | collar with call {ck.strike:.1f} ({ck.pct:+.0%}) sold @ ${call_prem:,.0f}: net cost ${put_cost-call_prem:,.0f} ({(put_cost-call_prem)/(spot*100):+.1%}), collared P&L {hedged+call_prem-call_val:+,.0f} ({(hedged+call_prem-call_val)/(spot*100):+.1%})"
            print(line)
            rows.append(dict(event=name,root=root,put_strike=pk.strike,put_cost_pct=put_cost/(spot*100),unhedged_pct=unh/(spot*100),hedged_pct=hedged/(spot*100)))
        break  # first root with data
pd.DataFrame(rows).to_csv("out/P_earnings_hedge_replay.csv",index=False)

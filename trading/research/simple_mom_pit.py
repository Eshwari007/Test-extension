"""Two simple, no-timing momentum portfolios on the point-in-time universe, 2021-2026, daily close marks, 10 bps per side on turnover.
A. Defensive Stage-1 sleeve: top-15 by 21d return among Stage-1 qualifiers, equal weight, rebalanced weekly; cash when SPY < EMA50.
B. Classic 12-1 momentum: top-20 by 12-month return skipping the last month, within 10% of 52w high, above SMA50, equal weight,
   rebalanced monthly; cash when SPY < EMA50. Also B without the regime switch."""
import os, sys, pickle, math, datetime as dt, numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE); sys.path.insert(0,os.path.join(HERE,".."))
import gajjala_scanner_us as g
ET=g.ET; C=os.path.join(HERE,"cache_pit")
daily=pickle.load(open(f"{C}/daily.pkl","rb")); spy=pickle.load(open(f"{C}/spy_daily.pkl","rb")); members=pickle.load(open(f"{C}/members.pkl","rb")); mdates=sorted(members)
def member_set(d): return members[mdates[max(np.searchsorted(mdates,d,side="right")-1,0)]]
S=spy.copy(); S.index=S.index.tz_convert(ET).date; sessions=list(S.index)
spy_e50=S.c.ewm(span=50,adjust=False).mean(); spy21=S.c/S.c.shift(21)-1
closes=pd.DataFrame({s:df.c.set_axis(df.index.tz_convert(ET).date) for s,df in daily.items()}).reindex(sessions)
vols=pd.DataFrame({s:df.v.set_axis(df.index.tz_convert(ET).date) for s,df in daily.items()}).reindex(sessions)
highs=pd.DataFrame({s:df.h.set_axis(df.index.tz_convert(ET).date) for s,df in daily.items()}).reindex(sessions)
r21=closes/closes.shift(21)-1; sma50=closes.rolling(50).mean(); dvol=(closes*vols).rolling(20).mean(); hi52=highs.rolling(252,min_periods=120).max()
r12_1=closes.shift(21)/closes.shift(252)-1
def run(pick_fn, rebalance_days, regime, label, cost=1e-3):
    eq=1.0; curve=[]; w=pd.Series(dtype=float); last_reb=None
    for i,d in enumerate(sessions):
        if i<260 or d<dt.date(2021,1,4): curve.append(np.nan); continue
        prev=sessions[i-1]
        # daily return of current holdings
        if len(w):
            r=(closes.loc[d,w.index]/closes.loc[prev,w.index]-1).fillna(0); eq*=1+float((w*r).sum())
        reb=(last_reb is None) or ((i-last_reb)>=rebalance_days)
        if reb:
            if regime and not (S.c[prev]>spy_e50[prev]): new=pd.Series(dtype=float)
            else:
                mem=[s for s in member_set(prev) if s in closes.columns]; picks=pick_fn(prev,mem)
                new=pd.Series(1/len(picks),index=picks) if len(picks) else pd.Series(dtype=float)
            turn=float((new.reindex(w.index.union(new.index)).fillna(0)-w.reindex(w.index.union(new.index)).fillna(0)).abs().sum())/2
            eq*=1-turn*2*cost; w=new; last_reb=i
        curve.append(eq)
    return pd.Series(curve,index=sessions).dropna()
def pick_A(d,mem):
    c=closes.loc[d,mem]; ok=(r21.loc[d,mem]>spy21[d])&(c>sma50.loc[d,mem])&(c>10)&(dvol.loc[d,mem]>25e6)&(c/hi52.loc[d,mem]-1>=-0.10)
    return list(r21.loc[d,mem][ok].dropna().nlargest(15).index)
def pick_B(d,mem):
    c=closes.loc[d,mem]; ok=(c>sma50.loc[d,mem])&(c>10)&(dvol.loc[d,mem]>25e6)&(c/hi52.loc[d,mem]-1>=-0.10)
    return list(r12_1.loc[d,mem][ok].dropna().nlargest(20).index)
curves={"SPY":S.c[S.index>=dt.date(2021,1,4)]/S.c[dt.date(2021,1,4)],
        "A. Stage-1 top-15, weekly, regime switch":run(pick_A,5,True,"A"),
        "B. 12-1 momentum top-20, monthly, regime switch":run(pick_B,21,True,"B"),
        "B2. 12-1 momentum top-20, monthly, no switch":run(pick_B,21,False,"B2")}
wins=[("2021",dt.date(2021,1,4),dt.date(2021,12,31)),("2022",dt.date(2022,1,3),dt.date(2022,12,30)),("2023",dt.date(2023,1,3),dt.date(2023,12,29)),("2024",dt.date(2024,1,2),dt.date(2024,12,31)),("2025",dt.date(2025,1,2),dt.date(2025,12,31)),("2026 YTD",dt.date(2026,1,2),dt.date(2026,10,9))]
print(f"{'strategy':48s} "+" ".join(f"{w[0]:>9s}" for w in wins)+f" {'total':>8s} {'CAGR':>7s} {'maxDD':>7s} {'beat SPY':>9s}")
spyr={}
for name,cv in curves.items():
    row=[]; beat=0
    for wn,a,b in wins:
        x=cv[(cv.index>=a)&(cv.index<=b)]; r=x.iloc[-1]/x.iloc[0]-1; row.append(r)
        if name=="SPY": spyr[wn]=r
        elif r>spyr[wn]: beat+=1
    yrs=(cv.index[-1]-cv.index[0]).days/365.25
    print(f"{name:48s} "+" ".join(f"{r:+9.1%}" for r in row)+f" {cv.iloc[-1]/cv.iloc[0]-1:+8.1%} {(cv.iloc[-1]/cv.iloc[0])**(1/yrs)-1:+7.1%} {(cv/cv.cummax()-1).min():7.1%} {'' if name=='SPY' else f'{beat} of 6':>9s}")
pd.DataFrame(curves).to_csv("out/simple_mom_pit.csv")

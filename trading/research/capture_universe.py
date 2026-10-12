"""Does the capture method generalize? Daily-bar test across all 516 names, Jan 2025 - Oct 9 2026."""
import sys, datetime as dt; sys.path.insert(0,'.')
import numpy as np, pandas as pd, data as D
ET=D.g.ET; daily=D.load("daily.pkl"); spyd=D.load("spy_daily.pkl")
S=spyd.copy(); S.index=S.index.tz_convert(ET).date; spy21=(S.c/S.c.shift(21)-1); spy_e50=S.c.ewm(span=50,adjust=False).mean()
start,end=dt.date(2025,1,2),dt.date(2026,10,9); IS_END=dt.date(2025,12,31)
def feats(df):
    d=df.copy(); d.index=d.index.tz_convert(ET).date
    d["e21"]=d.c.ewm(span=21,adjust=False).mean(); d["e50"]=d.c.ewm(span=50,adjust=False).mean(); d["s50"]=d.c.rolling(50).mean()
    d["hi20"]=d.h.rolling(20).max().shift(1); d["lo10"]=d.l.rolling(10).min().shift(1); d["hi52"]=d.h.rolling(252,min_periods=120).max().shift(1)
    d["r21"]=d.c/d.c.shift(21)-1; d["dvol"]=(d.c*d.v).rolling(20).mean(); d["rvol"]=d.v/d.v.rolling(20).mean().shift(1)
    d["spy21"]=spy21.reindex(d.index).values; d["spy_up"]=(S.c>spy_e50).reindex(d.index).values
    return d
F={s:feats(df) for s,df in daily.items()}
def run(label, ent, ex, stage1=False, max_hold=None):
    trades=[]
    for s,d in F.items():
        d=d[(d.index>=start-dt.timedelta(days=5))&(d.index<=end)]
        if len(d)<30: continue
        cl,hi,lo,op=d.c.values,d.h.values,d.l.values,d.o.values; idx=list(d.index); pos=None
        cols={k:d[k].values for k in ["e21","e50","s50","hi20","lo10","hi52","r21","dvol","rvol","spy21","spy_up"]}
        for k in range(1,len(idx)-1):
            if idx[k]<start: continue
            if pos is None:
                if np.isnan(cols["hi52"][k]) or np.isnan(cols["e50"][k]): continue
                if stage1 and not (cols["r21"][k]>cols["spy21"][k] and cl[k]>cols["s50"][k] and cl[k]>10 and cols["dvol"][k]>25e6 and cl[k]/cols["hi52"][k]-1>=-0.10): continue
                if ent(k,cl,hi,lo,cols): pos=(k+1,op[k+1])
            else:
                ei,ep=pos
                if ex(k,ei,ep,cl,hi,lo,cols) or (max_hold and k-ei>=max_hold-1):
                    trades.append((s,idx[ei],idx[k+1],op[k+1]/ep-1)); pos=None
        if pos: trades.append((s,idx[pos[0]],idx[-1],cl[-1]/pos[1]-1))
    t=pd.DataFrame(trades,columns=["symbol","entry","exit","ret"])
    def st(x):
        if x.empty: return "n=0"
        w=x.ret>0; return f"n={len(x):5d} win={w.mean():.0%} avg={x.ret.mean()*100:+.2f}% PF={x.ret[w].sum()/max(1e-9,-x.ret[~w].sum()):.2f} avg hold={(pd.to_datetime(x.exit)-pd.to_datetime(x.entry)).dt.days.mean():.0f}d"
    print(f"{label:62s} ALL {st(t)} | IS {st(t[t.entry<=IS_END])} | OOS {st(t[t.entry>IS_END])}",flush=True)
    return t
print("=== Universe-wide daily-bar capture tests (entries next open, exits next open) ===")
brk=lambda k,cl,hi,lo,c: cl[k]>c["hi20"][k] and cl[k]>c["e50"][k]
run("B0. 20d breakout + >EMA50, exit <EMA21  (all 516 names, no filter)", brk, lambda k,ei,ep,cl,hi,lo,c: cl[k]<c["e21"][k])
run("B1. same + SPY above EMA50", lambda k,cl,hi,lo,c: brk(k,cl,hi,lo,c) and c["spy_up"][k], lambda k,ei,ep,cl,hi,lo,c: cl[k]<c["e21"][k])
run("B2. same + Stage-1 filter (RS>SPY, >SMA50, $25M, within 10% 52w hi)", brk, lambda k,ei,ep,cl,hi,lo,c: cl[k]<c["e21"][k], stage1=True)
run("B3. B2 + breakout volume >= 1.5x 20d avg", lambda k,cl,hi,lo,c: brk(k,cl,hi,lo,c) and c["rvol"][k]>=1.5, lambda k,ei,ep,cl,hi,lo,c: cl[k]<c["e21"][k], stage1=True)
run("B4. B2, exit <EMA21 or -8% stop", brk, lambda k,ei,ep,cl,hi,lo,c: cl[k]<c["e21"][k] or lo[k]<=ep*0.92, stage1=True)
run("B5. B2, exit <10-day low", brk, lambda k,ei,ep,cl,hi,lo,c: cl[k]<c["lo10"][k], stage1=True)
run("B6. B2, exit <EMA50", brk, lambda k,ei,ep,cl,hi,lo,c: cl[k]<c["e50"][k], stage1=True)
run("A.  Stage-1 any day, hold 3d, 5% stop (Gajjala daily proxy)", lambda k,cl,hi,lo,c: True, lambda k,ei,ep,cl,hi,lo,c: lo[k]<=ep*0.95, stage1=True, max_hold=3)
run("A2. Stage-1 + 20d breakout day, hold 3d, 5% stop", brk, lambda k,ei,ep,cl,hi,lo,c: lo[k]<=ep*0.95, stage1=True, max_hold=3)
run("J.  New 52w-high close (Stage-1), exit <EMA21", lambda k,cl,hi,lo,c: cl[k]>c["hi52"][k], lambda k,ei,ep,cl,hi,lo,c: cl[k]<c["e21"][k], stage1=True)

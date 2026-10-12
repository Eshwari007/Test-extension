import sys, datetime as dt; sys.path.insert(0,'.')
import numpy as np, pandas as pd, data as D
exec(open('p_deep_dive.py').read().split('print("=== 1.')[0])  # reuse setup (P, yr, S, etc.)
cl, hi, lo = yr.c.values, yr.h.values, yr.l.values; e21, e50 = yr.ema21.values, yr.ema50.values
hi20 = pd.Series(hi).rolling(20).max().shift(1).values; hi52p = P.h.rolling(252).max().shift(1).reindex(yr.index).values
idx = list(yr.index)
def run(ent, ex, label):
    pos=None; out=[]
    for k in range(1,len(idx)-1):
        if pos is None:
            if ent(k): pos=(k+1, yr.o.iloc[k+1])
        elif ex(k,pos[0],pos[1]):
            out.append((idx[pos[0]], idx[k+1], pos[1], yr.o.iloc[k+1], yr.o.iloc[k+1]/pos[1]-1)); pos=None
    if pos: out.append((idx[pos[0]], idx[-1], pos[1], cl[-1], cl[-1]/pos[1]-1))
    t=pd.DataFrame(out,columns=['entry','exit','in_px','out_px','ret']); print(f"\n{label}: total {np.prod(1+t.ret)-1:+.1%}"); print(t.round(2).to_string(index=False)); return t
B=run(lambda k: cl[k]>hi20[k] and cl[k]>e50[k], lambda k,ei,ep: cl[k]<e21[k], "B. 20-day high breakout (close>EMA50), exit close<EMA21")
J=run(lambda k: cl[k]>hi52p[k] and cl[k-1]<=hi52p[k-1], lambda k,ei,ep: cl[k]<e21[k], "J. New 52-week-high close, exit close<EMA21 (fixed)")
B.to_csv('out/P_methodB_trades.csv',index=False)
print("\n=== Tuned Gajjala swing strategy's actual trades in P (5-min entries, 5% stop, 3-session hold) ===")
ct=pd.read_csv('out/chosen_trades.csv'); pt=ct[ct.symbol=='P']
print(pt[['session','time','entry','stop','exit_time','exits','R','pnl']].to_string(index=False) if len(pt) else "none")
print(f"P trades: {len(pt)}, total R {pt.R.sum():+.1f}, P&L ${pt.pnl.sum():,.0f} on $100k/10% sizing")
# chart
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig,(ax,av)=plt.subplots(2,1,figsize=(13,7.5),sharex=True,gridspec_kw={'height_ratios':[3,1]})
x=pd.to_datetime(pd.Series(yr.index))
ax.plot(x,yr.c.values,color='black',lw=1.2,label='P close'); ax.plot(x,yr.ema21.values,color='tab:blue',lw=1,label='EMA21'); ax.plot(x,yr.ema50.values,color='tab:orange',lw=1,label='EMA50')
spy_n=S.c.reindex(yr.index); ax.plot(x,spy_n.values/spy_n.iloc[0]*yr.c.iloc[0],color='gray',lw=0.9,ls='--',label='SPY (rebased)')
for _,r in B.iterrows():
    ax.axvspan(pd.Timestamp(r.entry),pd.Timestamp(r.exit),color='green' if r.ret>0 else 'red',alpha=0.12)
    ax.annotate(f"{r.ret:+.0%}",(pd.Timestamp(r.exit),r.out_px),fontsize=8,color='green' if r.ret>0 else 'red')
for d,lab in ((dt.date(2025,12,3),'Q3 FY26 earnings -27%'),(dt.date(2026,5,28),'Q1 FY27 earnings -15%'),(dt.date(2026,8,27),'Q2 FY27 earnings -9%')):
    ax.axvline(pd.Timestamp(d),color='red',lw=0.8,ls=':'); ax.text(pd.Timestamp(d),yr.c.max()*0.98,lab,rotation=90,fontsize=7,va='top',color='red')
for _,r in pt.iterrows(): ax.scatter(pd.Timestamp(r.session),r.entry,marker='^',color='purple',s=40,zorder=5)
ax.scatter([],[],marker='^',color='purple',label='Gajjala swing entries (5-min)'); ax.legend(loc='upper left',fontsize=8); ax.set_title('Everpure (P), Oct 9 2025 to Oct 9 2026: shaded = 20-day breakout / EMA21-trail trades'); ax.grid(alpha=.3)
av.bar(x,yr.v.values/1e6,color='steelblue',width=1); av.set_ylabel('volume (M)'); av.grid(alpha=.3)
fig.tight_layout(); fig.savefig('out/P_chart.png',dpi=130); print('chart saved')

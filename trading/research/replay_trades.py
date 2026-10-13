"""Full trade blotter of the recommended configuration: $100k, half swing book (10 slots x 10%), half trend book (10 slots x 10%),
Jan 2 2025 -> Oct 9 2026, 5 bps slippage per side. Writes out/blotter_*.csv and out/trade_blotter.xlsx."""
import sys, io, contextlib, math, heapq, datetime as dt, numpy as np, pandas as pd; sys.path.insert(0,'.')
from engine import Dataset, Params, run
from run import ALL
import portfolio as P, data as D
ds=Dataset(); P.init(ds)
names=pd.read_csv('../data/sp500.csv').set_index('Symbol')['Security'].to_dict()
# ---------- swing book: record taken trades ----------
C=Params(mode="orb",orb_bars=3,vol_mult=1.5,stop_mode="pct",stop_pct=5,targets=(),trail="none",hold="overnight",max_hold_days=3,earliest="09:45",max_off_high=10)
sw=run(ds,C,*ALL).sort_values("time").reset_index(drop=True)
sw["exit_px"]=sw.exits.str.split("@").str[1].str.split(":").str[0].astype(float); sw["reason"]=sw.exits.str.extract(r":(\w+)$")[0]
def swing_book(tr,max_pos,size_frac,slip_bps,start_eq):
    events=[(r.time,0,k) for k,r in tr.iterrows()]; heapq.heapify(events)
    cash=start_eq; open_pos={}; taken=[]
    while events:
        t,kind,k=heapq.heappop(events)
        if kind==-1:
            p=open_pos.pop(k); cash+=p["qty"]*p["exit_px"]*(1-slip_bps/1e4); continue
        r=tr.loc[k]
        if len(open_pos)>=max_pos: continue
        eq=cash+sum(p["qty"]*p["entry"] for p in open_pos.values()); px=r.entry*(1+slip_bps/1e4); qty=math.floor(eq*size_frac/px)
        if qty<=0 or qty*px>cash: continue
        cash-=qty*px; open_pos[k]=dict(qty=qty,entry=px,exit_px=r.exit_px); heapq.heappush(events,(r.exit_time,-1,k))
        taken.append(dict(book="swing",symbol=r.symbol,company=names.get(r.symbol,""),entry_time=r.time,exit_time=r.exit_time,entry=round(px,2),exit=round(r.exit_px*(1-slip_bps/1e4),2),shares=qty,
                          cost=round(qty*px,0),pnl=round(qty*(r.exit_px*(1-slip_bps/1e4)-px),0),ret=round(r.exit_px*(1-slip_bps/1e4)/px-1,4),reason=r.reason,stop=r.stop))
    return pd.DataFrame(taken)
SW=swing_book(sw,10,0.10,5,50_000)
# ---------- trend book: record taken trades ----------
src=open('capture_portfolio.py').read().split('print(f"SPY:')[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
tr=sets["B3 breakout+vol, Stage-1, exit <EMA21"].copy()
tr["in_px"]=[F[s].o.get(d,np.nan) for s,d in zip(tr.symbol,tr.entry)]; tr["out_px"]=tr.in_px*(1+tr.ret)
# collar adjustment (earnings-sized gap days inside the hold clipped to [-10%,+15%])
G=pd.read_csv('out/gap_events.csv',parse_dates=['date']); G['date']=G.date.dt.date
tr["collar_adj"]=[sum(min(max(e.day,-0.10),0.15)-e.day for _,e in G[(G.symbol==r.symbol)&(G.date>r.entry)&(G.date<=r.exit)].iterrows()) for _,r in tr.iterrows()]
tr["ret"]=tr.ret+tr.collar_adj; tr["out_px"]=tr.in_px*(1+tr.ret)
def trend_book(t,max_pos,size,slip,start_eq):
    t=t.sort_values(["entry","symbol"]).reset_index(drop=True); by_day=t.groupby("entry"); cash=start_eq; open_pos={}; taken=[]
    for d in sessions:
        for k in [k for k,p in open_pos.items() if p["exit"]==d]:
            p=open_pos.pop(k); cash+=p["qty"]*p["out_px"]*(1-slip)
        if d in by_day.groups:
            for k,r in by_day.get_group(d).iterrows():
                if len(open_pos)>=max_pos: continue
                mv=sum(p["qty"]*closes[p["sym"]].get(d,p["in_px"]) for p in open_pos.values()); px=r.in_px*(1+slip); qty=math.floor((cash+mv)*size/px)
                if qty<=0 or qty*px>cash: continue
                cash-=qty*px; open_pos[k]=dict(sym=r.symbol,qty=qty,in_px=px,exit=r.exit,out_px=r.out_px)
                taken.append(dict(book="trend",symbol=r.symbol,company=names.get(r.symbol,""),entry_time=r.entry,exit_time=r.exit,entry=round(px,2),exit=round(r.out_px*(1-slip),2),shares=qty,
                                  cost=round(qty*px,0),pnl=round(qty*(r.out_px*(1-slip)-px),0),ret=round(r.out_px*(1-slip)/px-1,4),reason="EMA21 exit" if r.exit<dt.date(2026,10,9) else "open at end",stop=round(px*0.92,2),collar_adj=round(r.collar_adj,4)))
    return pd.DataFrame(taken)
TR=trend_book(tr,10,0.10,5e-4,50_000)
# ---------- outputs ----------
for b,df in (("swing",SW),("trend",TR)):
    print(f"{b}: {len(df)} trades, {df.symbol.nunique()} symbols, P&L ${df.pnl.sum():,.0f}, win {(df.pnl>0).mean():.0%}")
SW["entry_date"]=pd.to_datetime(SW.entry_time).dt.date; SW["exit_date"]=pd.to_datetime(SW.exit_time).dt.date; TR["entry_date"]=TR.entry_time; TR["exit_date"]=TR.exit_time
cols=["book","symbol","company","entry_date","exit_date","entry","exit","shares","cost","pnl","ret","reason"]
ALLT=pd.concat([SW[cols+["entry_time"]],TR[cols+["collar_adj"]]],ignore_index=True).sort_values("entry_date")
ALLT.to_csv("out/blotter_all.csv",index=False); SW.to_csv("out/blotter_swing.csv",index=False); TR.to_csv("out/blotter_trend.csv",index=False)
by=ALLT.groupby("symbol").agg(company=("company","first"),trades=("pnl","size"),swing=("book",lambda x:(x=="swing").sum()),trend=("book",lambda x:(x=="trend").sum()),wins=("pnl",lambda x:(x>0).sum()),pnl=("pnl","sum"),best=("pnl","max"),worst=("pnl","min")).sort_values("pnl",ascending=False)
by.to_csv("out/blotter_by_symbol.csv")
print(f"\nTOTAL: {len(ALLT)} trades across {ALLT.symbol.nunique()} stocks; P&L ${ALLT.pnl.sum():,.0f}; top 10 stocks = ${by.pnl.head(10).sum():,.0f}; {int((by.pnl>0).sum())} stocks net positive, {int((by.pnl<=0).sum())} net negative")
print("\nTop 25 stocks by P&L:"); print(by.head(25).to_string())
print("\nBottom 10:"); print(by.tail(10).to_string())
print("\nTrend-book trades (the big ones), top 15 by P&L:"); print(TR.nlargest(15,"pnl")[["symbol","entry_date","exit_date","entry","exit","shares","pnl","ret"]].to_string(index=False))
mo=ALLT.assign(m=pd.to_datetime(ALLT.entry_date).dt.to_period("M")).groupby(["m","book"]).pnl.agg(["size","sum"]).unstack("book").fillna(0); print("\nTrades and P&L by entry month:"); print(mo.to_string())
with pd.ExcelWriter("out/trade_blotter.xlsx") as xw:
    by.to_excel(xw,sheet_name="By stock"); ALLT.drop(columns=["entry_time"]).to_excel(xw,sheet_name="All trades",index=False)
    SW.drop(columns=["entry_time","exit_time"]).to_excel(xw,sheet_name="Swing book",index=False); TR.drop(columns=["entry_time","exit_time"]).to_excel(xw,sheet_name="Trend book",index=False)
print("\nwrote out/trade_blotter.xlsx")

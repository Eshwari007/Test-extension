"""Point-in-time universe: membership per date from fja05680/sp500, daily bars for every member since 2020-06 from Alpaca.
Writes cache_pit/daily.pkl (dict sym->DataFrame), cache_pit/spy_daily.pkl, cache_pit/members.pkl (date->set), cache_pit/coverage.csv."""
import os, sys, pickle, time, datetime as dt, numpy as np, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE); sys.path.insert(0,os.path.join(HERE,".."))
import gajjala_scanner_us as g
PIT=os.path.join(HERE,"..","data","pit","SandP_500_Historical_Components_and_Changes_Updated.csv")
CACHE=os.path.join(HERE,"cache_pit"); os.makedirs(CACHE,exist_ok=True)
pit=pd.read_csv(PIT); pit["date"]=pd.to_datetime(pit.date).dt.date; pit=pit.sort_values("date")
print("PIT file: rows",len(pit),"first",pit.date.iloc[0],"last",pit.date.iloc[-1],"tickers on last row",len(pit.tickers.iloc[-1].split(",")))
pit=pit[pit.date>=dt.date(2020,6,1)]
members={r.date:set(r.tickers.split(",")) for r in pit.itertuples()}
# membership between listed change dates = the previous listed row; build a daily lookup lazily in the consumer
union=sorted(set().union(*members.values()))
print(f"{len(union)} distinct tickers in the index at some point since 2020-06-01")
# Alpaca symbols: dots for class shares (BRK.B, BF.B) are fine; drop obvious bad tokens
syms=[s for s in union if s and s.replace(".","").isalnum()]
t0=time.time(); daily={}
for i in range(0,len(syms),100):
    chunk=syms[i:i+100]
    try: got=g.get_bars(chunk,"1Day","2020-01-01","2026-10-10T00:00:00Z")
    except Exception as e: print("batch error",i,e); got={}
    daily.update(got); print(f"  {i+len(chunk)}/{len(syms)} symbols, {len(daily)} with data, {time.time()-t0:.0f}s",flush=True)
spy=g.get_bars(["SPY"],"1Day","2020-01-01","2026-10-10T00:00:00Z")["SPY"]
pickle.dump(daily,open(os.path.join(CACHE,"daily.pkl"),"wb")); pickle.dump(spy,open(os.path.join(CACHE,"spy_daily.pkl"),"wb")); pickle.dump(members,open(os.path.join(CACHE,"members.pkl"),"wb"))
cov=[]
for d,ms in sorted(members.items()):
    have=sum(1 for s in ms if s in daily and len(daily[s][daily[s].index.tz_convert(g.ET).date<=d])>0)
    cov.append(dict(date=d,members=len(ms),with_data=have))
cov=pd.DataFrame(cov); cov.to_csv(os.path.join(CACHE,"coverage.csv"),index=False)
print("coverage (members with Alpaca data) by year:"); print(cov.assign(y=pd.to_datetime(cov.date).dt.year).groupby("y").agg(members=("members","mean"),with_data=("with_data","mean")).round(0).to_string())
missing=[s for s in syms if s not in daily]; print(f"{len(missing)} tickers with no Alpaca data, e.g. {missing[:40]}")
print("DONE")

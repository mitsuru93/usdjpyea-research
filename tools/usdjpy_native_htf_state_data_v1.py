#!/usr/bin/env python3
"""Data and indicator primitives for the frozen native H4/H1 family."""
from __future__ import annotations
import hashlib, math
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd

PIP=0.01
FOLDS={
 "2023H1":(pd.Timestamp("2023-01-01T00:00:00Z"),pd.Timestamp("2023-07-01T00:00:00Z")),
 "2023H2":(pd.Timestamp("2023-07-01T00:00:00Z"),pd.Timestamp("2024-01-01T00:00:00Z")),
 "2024H1":(pd.Timestamp("2024-01-01T00:00:00Z"),pd.Timestamp("2024-07-01T00:00:00Z")),
 "2024H2":(pd.Timestamp("2024-07-01T00:00:00Z"),pd.Timestamp("2025-01-01T00:00:00Z")),
}
EXPECTED_CELLS=[
 ("N_H4F3S12_H1F4S16",3,12,4,16,0,0),("N_H4F3S12_H1F8S32",3,12,8,32,0,1),
 ("N_H4F6S24_H1F4S16",6,24,4,16,1,0),("N_H4F6S24_H1F8S32",6,24,8,32,1,1),
 ("N_H4F12S48_H1F4S16",12,48,4,16,2,0),("N_H4F12S48_H1F8S32",12,48,8,32,2,1),
]

def file_sha(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()

def nth_sunday(year:int,month:int,nth:int,hour:int)->pd.Timestamp:
 first=datetime(year,month,1,hour,tzinfo=timezone.utc)
 return pd.Timestamp(first+timedelta(days=(6-first.weekday())%7+7*(nth-1)))
def is_us_dst(ts:pd.Timestamp)->bool:return nth_sunday(ts.year,3,2,7)<=ts<nth_sunday(ts.year,11,1,6)
def server_to_utc(server:pd.Timestamp)->pd.Timestamp:
 winter=server-pd.Timedelta(hours=2);return server-pd.Timedelta(hours=3) if is_us_dst(winter) else winter
def utc_to_server(utc:pd.Timestamp)->pd.Timestamp:return utc+pd.Timedelta(hours=3 if is_us_dst(utc) else 2)
def hard_excluded(logical_utc:pd.Timestamp)->bool:
 h=logical_utc.hour;return (20<=h<23) if is_us_dst(logical_utc) else (21<=h<24)

def load_m15_2023(path:Path)->pd.DataFrame:
 raw=pd.read_csv(path);server_first=pd.to_datetime(raw["first_timestamp_mt4_server"],utc=True,errors="raise")
 logical_server=server_first.dt.floor("15min");accepted=pd.DatetimeIndex([server_to_utc(x) for x in server_first]);logical=pd.DatetimeIndex([server_to_utc(x) for x in logical_server])
 frame=pd.DataFrame({"logical_utc":logical,"logical_server":logical_server,"accepted_ts":accepted,"open":pd.to_numeric(raw["open"],errors="raise"),"high":pd.to_numeric(raw["high"],errors="raise"),"low":pd.to_numeric(raw["low"],errors="raise"),"close":pd.to_numeric(raw["close"],errors="raise"),"default_cost_pips":0.5,"year":2023}).sort_values("logical_utc").reset_index(drop=True)
 assert len(frame)==24825 and not frame.logical_utc.duplicated().any();return frame

def load_m15_2024(path:Path)->pd.DataFrame:
 raw=pd.read_csv(path,compression="gzip");logical=pd.to_datetime(raw["timestamp_utc"],utc=True,errors="raise");server=pd.DatetimeIndex([utc_to_server(x) for x in logical]);spread=pd.to_numeric(raw["spread_mean_pips"],errors="raise")
 frame=pd.DataFrame({"logical_utc":logical,"logical_server":server,"accepted_ts":logical,"open":pd.to_numeric(raw["mid_open"],errors="raise"),"high":pd.to_numeric(raw["mid_high"],errors="raise"),"low":pd.to_numeric(raw["mid_low"],errors="raise"),"close":pd.to_numeric(raw["mid_close"],errors="raise"),"default_cost_pips":np.maximum(0.5,spread),"year":2024}).sort_values("logical_utc").reset_index(drop=True)
 assert len(frame)==24439 and not frame.logical_utc.duplicated().any();return frame

def aggregate_exact(m15:pd.DataFrame,frequency:str,slots:int)->pd.DataFrame:
 bucket=m15.logical_server.dt.floor(frequency);work=m15.assign(bucket_server=bucket)
 grouped=work.groupby("bucket_server",sort=True).agg(constituent=("logical_server","size"),open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"))
 grouped["exact"]=[set(work.loc[work.bucket_server==start,"logical_server"])==set(pd.date_range(start,periods=slots,freq="15min")) for start in grouped.index]
 grouped=grouped[grouped.exact].copy();grouped["information_utc"]=[server_to_utc(start+pd.tseries.frequencies.to_offset(frequency)) for start in grouped.index]
 return grouped.reset_index().sort_values("information_utc").reset_index(drop=True)

def add_state(frame:pd.DataFrame,fast:int,slow:int,prefix:str)->pd.DataFrame:
 work=frame.copy();fast_ema=work.close.ewm(span=fast,adjust=False,min_periods=slow).mean();slow_ema=work.close.ewm(span=slow,adjust=False,min_periods=slow).mean();state=pd.Series(0,index=work.index,dtype="int8")
 state.loc[fast_ema>slow_ema]=1;state.loc[fast_ema<slow_ema]=-1;work[f"{prefix}_fast"]=fast_ema;work[f"{prefix}_slow"]=slow_ema;work[f"{prefix}_state"]=state
 previous=state.shift(1).fillna(0).astype("int8");transition=pd.Series(0,index=work.index,dtype="int8");transition.loc[(previous==-1)&(state==1)]=1;transition.loc[(previous==1)&(state==-1)]=-1;work[f"{prefix}_transition"]=transition;return work

def execution_index(times:np.ndarray,info:pd.Timestamp)->int|None:
 i=int(np.searchsorted(times,np.datetime64(info.to_datetime64()),side="left"));return i if i<len(times) else None

def profit_factor(values:pd.Series)->float:
 gain=float(values[values>0].sum());loss=float(-values[values<0].sum())
 if loss==0:return math.inf if gain>0 else 0.0
 return gain/loss

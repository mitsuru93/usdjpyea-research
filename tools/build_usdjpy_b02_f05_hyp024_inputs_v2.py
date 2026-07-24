#!/usr/bin/env python3
from __future__ import annotations
import argparse, gzip, hashlib, io, json, re
from pathlib import Path
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
PIP=0.01
EXPECTED={
 'm15_2023':'4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78',
 'm15_2024h1':'766be5ebba158e5b40f5da5d66929b4da8a25d42a8716b1e591d7c09dd87c2a3',
 'events_2024h1':'9560d6382e2457eaec83415316fb59d4989244d49c9977ce76cbdd717f32f09a',
 'events_2024h2':'a5a871d7105c6e68548e804c9ab517ee6bc0b08553474b158799f47ebd32edcd',
}
B02={'family':'session_range_breakout','reference_start_hour':0,'reference_end_hour_exclusive':7,'entry_start_hour':7,'entry_end_hour_inclusive':12}
F05={'family':'donchian_channel_breakout','lookback_bars':96,'entry_hours_utc':list(range(20))}

def sha256_file(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1<<20),b''): h.update(chunk)
 return h.hexdigest()

def nth_sunday(y,m,n,h):
 d=datetime(y,m,1,h,tzinfo=timezone.utc)
 return pd.Timestamp(d+timedelta(days=(6-d.weekday())%7+7*(n-1)))
def us_dst(ts): return ts>=nth_sunday(ts.year,3,2,7) and ts<nth_sunday(ts.year,11,1,6)
def server_to_hist_utc(s):
 wc=s-pd.Timedelta(hours=2)
 return s-pd.Timedelta(hours=3) if us_dst(wc) else wc

def enrich(d):
 d=d.copy(); d['timestamp_utc']=pd.to_datetime(d.timestamp_utc,utc=True); d=d.sort_values('timestamp_utc').reset_index(drop=True)
 d['date_utc']=d.timestamp_utc.dt.strftime('%Y-%m-%d'); d['hour_utc']=d.timestamp_utc.dt.hour.astype(int)
 return d

def load_2023(path:Path):
 d=pd.read_csv(path)
 true=pd.to_datetime(d.timestamp_utc,utc=True); server=pd.to_datetime(d.first_timestamp_mt4_server,utc=True)
 hist=pd.DatetimeIndex([server_to_hist_utc(x) for x in server])
 assert int((hist!=true).sum())==1543
 assert int(hist.duplicated().sum())==0 and hist.is_monotonic_increasing
 return enrich(pd.DataFrame({'timestamp_utc':hist,'open':d.open.astype(float),'high':d.high.astype(float),'low':d.low.astype(float),'close':d.close.astype(float)}))

def hard_excl(entry):
 local=entry.dt.tz_convert(ZoneInfo('America/New_York')).dt.time
 return (local>=time(16,0))&(local<time(19,0))
def first_dir_day(side,b):
 keep=pd.Series(0,index=side.index,dtype='int8'); s=pd.DataFrame({'side':side,'date':b.date_utc,'ts':b.timestamp_utc}); s=s[s.side.isin([1,-1])]
 if len(s):
  idx=s.sort_values('ts').groupby(['date','side'],sort=False).head(1).index; keep.loc[idx]=side.loc[idx].astype('int8')
 return keep

def build_signal(b,kind):
 s=pd.Series(0,index=b.index,dtype='int8')
 if kind=='B02':
  ref=b[(b.hour_utc>=0)&(b.hour_utc<7)].groupby('date_utc').agg(hi=('high','max'),lo=('low','min'))
  r=b[['date_utc']].join(ref,on='date_utc'); allow=(b.hour_utc>=7)&(b.hour_utc<=12)
  s.loc[allow&(b.close>r.hi)]=1; s.loc[allow&(b.close<r.lo)]=-1; s=first_dir_day(s,b)
 else:
  entry=b.timestamp_utc.shift(-1); allow=entry.dt.hour.isin(range(20)); n=96
  hi=b.high.shift(1).rolling(n,min_periods=n).max(); lo=b.low.shift(1).rolling(n,min_periods=n).min()
  s.loc[allow&(b.close>hi)&(b.close.shift(1)<=hi.shift(1))]=1
  s.loc[allow&(b.close<lo)&(b.close.shift(1)>=lo.shift(1))]=-1
 return s

def historical_2023_trades(b):
 start=pd.Timestamp('2023-01-01T00:00:00Z'); end=pd.Timestamp('2024-01-01T00:00:00Z'); frames=[]
 for kind,cap in [('B02',48),('F05',32)]:
  raw=build_signal(b,kind); w=pd.DataFrame({'signal_utc':b.timestamp_utc,'entry_utc':b.timestamp_utc.shift(-1),'side':raw})
  w=w[w.side.isin([1,-1])&w.entry_utc.notna()].copy(); w=w[(w.entry_utc>=start)&(w.entry_utc<end)]; w=w[~hard_excl(w.entry_utc)].copy(); w['strategy']=kind; w['cap_bars']=cap
  if kind=='B02':
   counts=b[(b.hour_utc>=0)&(b.hour_utc<7)].groupby('date_utc').size(); dates=w.signal_utc.dt.strftime('%Y-%m-%d'); w=w[dates.map(counts).fillna(0).to_numpy()>=28]
  frames.append(w)
 s=pd.concat(frames).sort_values(['entry_utc','strategy'],kind='mergesort').reset_index(drop=True); mp=pd.Series(b.index,index=b.timestamp_utc).to_dict(); rows=[]
 for r in s.itertuples(index=False):
  ei=int(mp[r.entry_utc]); xi=ei+int(r.cap_bars); side=int(r.side); entry_bid=float(b.open.iloc[ei]); closed=xi<len(b) and b.timestamp_utc.iloc[xi]<end
  if not closed: continue
  close_bid=float(b.open.iloc[xi]); gross=side*(close_bid-entry_bid)/PIP-0.5; realized=int(round(gross*10))
  rows.append({'fold':'2023H1' if r.entry_utc<pd.Timestamp('2023-07-01T00:00:00Z') else '2023H2','strategy':r.strategy,'signal_utc':r.signal_utc,'entry_utc':r.entry_utc,'close_utc':b.timestamp_utc.iloc[xi],'side':side,'entry_bid':entry_bid,'realized_pl_jpy':realized})
 return pd.DataFrame(rows)

def parse_event_trades(path:Path,fold:str,include_period_mark:bool):
 d=pd.read_csv(path); o=d[d.event=='order_opened'][['ticket','strategy','signal_utc','entry_utc','side','price']].rename(columns={'price':'open_price'}); c=d[d.event=='order_closed'][['ticket','utc_time','gross_pips']].rename(columns={'utc_time':'close_utc'})
 t=o.merge(c,on='ticket',how='left',validate='one_to_one'); t['signal_utc']=pd.to_datetime(t.signal_utc,utc=True);t['entry_utc']=pd.to_datetime(t.entry_utc,utc=True);t['close_utc']=pd.to_datetime(t.close_utc,utc=True)
 t['entry_bid']=(t.open_price-np.where(t.side.eq(1),0.005,0.0)).round(3); t['realized_pl_jpy']=(t.gross_pips*10).round()
 if include_period_mark:
  miss=t.close_utc.isna(); assert miss.sum()==1; p=d[d.event=='period_end_open_position'].iloc[0]; snaps=d[d.event=='portfolio_snapshot'].copy();snaps['obs']=pd.to_datetime(snaps.utc_time,utc=True);snaps=snaps[snaps.obs.dt.year==2024]
  t.loc[miss,'close_utc']=snaps.obs.max(); floating=int(round(float(re.search(r'floating_pl=([-0-9.]+)',str(p.detail)).group(1))));t.loc[miss,'realized_pl_jpy']=floating
 else: t=t[t.close_utc.notna()].copy()
 t['fold']=fold
 return t[['fold','strategy','signal_utc','entry_utc','close_utc','side','entry_bid','realized_pl_jpy']]

def load_h1_bars(path:Path):
 d=pd.read_csv(path); return enrich(pd.DataFrame({'timestamp_utc':pd.to_datetime(d.utc_time,utc=True),'open':d.open.astype(float),'high':d.high.astype(float),'low':d.low.astype(float),'close':d.close.astype(float)}))
def load_h2_open_bars(path:Path):
 d=pd.read_csv(path); s=d[d.event=='portfolio_snapshot'].copy();s['timestamp_utc']=pd.to_datetime(s.utc_time,utc=True);s=s[s.timestamp_utc.dt.year==2024].sort_values('timestamp_utc').drop_duplicates('timestamp_utc',keep='last')
 return enrich(pd.DataFrame({'timestamp_utc':s.timestamp_utc,'open':s.price.astype(float),'high':s.price.astype(float),'low':s.price.astype(float),'close':s.price.astype(float)}))
def add_indicators(b):
 x=b.copy(); op=x.open.astype(float); x['mom4']=(op-op.shift(4))/PIP; ema20=op.ewm(span=20,adjust=False).mean(); fast=op.ewm(span=12,adjust=False).mean(); slow=op.ewm(span=26,adjust=False).mean(); macd=fast-slow; sig=macd.ewm(span=9,adjust=False).mean();x['ema20']=ema20;x['macd_hist']=macd-sig;return x

def zfmt(s): return pd.to_datetime(s,utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
def trade_id(fold,strategy,entry,side): return f'{fold}|{strategy}|{pd.Timestamp(entry)}|{int(side)}'
def build_states(trades,bars_by_fold):
 rows=[]
 for fold in ['2023H1','2023H2','2024H1','2024H2']:
  b=add_indicators(bars_by_fold[fold]); tt=trades[trades.fold==fold]
  for tr in tt.itertuples(index=False):
   g=b[(b.timestamp_utc>=tr.entry_utc)&(b.timestamp_utc<=tr.close_utc)]
   assert len(g)>0 and g.timestamp_utc.iloc[0]==tr.entry_utc
   tid=trade_id(fold,tr.strategy,tr.entry_utc,tr.side); temp=[]
   for j,r in enumerate(g.itertuples(index=False)):
    executable=round(int(tr.side)*(float(r.open)-float(tr.entry_bid))/PIP-0.5,1)
    temp.append({'trade_id':tid,'observation_index':j,'observation_utc':r.timestamp_utc,'bid_open':round(float(r.open),3),'executable_pips':executable,'path_class':'','mom4_dir_pips':round(int(tr.side)*float(r.mom4),8) if pd.notna(r.mom4) else np.nan,'macd_hist_dir_pips':round(int(tr.side)*float(r.macd_hist)/PIP,8) if pd.notna(r.macd_hist) else np.nan,'price_ema20_dir_pips':round(int(tr.side)*(float(r.open)-float(r.ema20))/PIP,8) if pd.notna(r.ema20) else np.nan})
   mx=max(x['executable_pips'] for x in temp); realized=float(tr.realized_pl_jpy)
   pc='WINNER' if realized>0 else ('P1_GIVEBACK_TO_LOSS' if mx>=10.0 else ('P2_MINOR_FAVORABLE_THEN_LOSS' if mx>0.0 else 'P3_NEVER_PROFITABLE'))
   for x in temp: x['path_class']=pc
   rows.extend(temp)
 return pd.DataFrame(rows)

def deterministic_gzip(data:bytes)->bytes:
 out=io.BytesIO()
 with gzip.GzipFile(filename='',mode='wb',fileobj=out,compresslevel=9,mtime=0) as gz: gz.write(data)
 return out.getvalue()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--m15-2023',type=Path,required=True);ap.add_argument('--m15-2024h1',type=Path,required=True);ap.add_argument('--events-2024h1',type=Path,required=True);ap.add_argument('--events-2024h2',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 actual={'m15_2023':sha256_file(a.m15_2023),'m15_2024h1':sha256_file(a.m15_2024h1),'events_2024h1':sha256_file(a.events_2024h1),'events_2024h2':sha256_file(a.events_2024h2)};assert actual==EXPECTED,(actual,EXPECTED)
 b23=load_2023(a.m15_2023); b1=load_h1_bars(a.m15_2024h1); b2=load_h2_open_bars(a.events_2024h2)
 trades=pd.concat([historical_2023_trades(b23),parse_event_trades(a.events_2024h1,'2024H1',False),parse_event_trades(a.events_2024h2,'2024H2',True)],ignore_index=True)
 trades=trades.sort_values(['fold','entry_utc','strategy'],kind='mergesort').reset_index(drop=True);assert len(trades)==1882
 states=build_states(trades,{'2023H1':b23,'2023H2':b23,'2024H1':b1,'2024H2':b2});assert len(states)==68955 and states.trade_id.nunique()==1882
 classes=states.groupby('trade_id',sort=False).path_class.first().reset_index();parts=classes.trade_id.str.split('|',expand=True);classes['fold']=parts[0];classes['strategy']=parts[1]
 counts={f'{s}_{f}':g.path_class.value_counts().sort_index().to_dict() for (f,s),g in classes.groupby(['fold','strategy'],sort=False)}
 expected_counts={
 'B02_2023H1':{'P1_GIVEBACK_TO_LOSS':30,'P2_MINOR_FAVORABLE_THEN_LOSS':16,'P3_NEVER_PROFITABLE':14,'WINNER':61},'F05_2023H1':{'P1_GIVEBACK_TO_LOSS':88,'P2_MINOR_FAVORABLE_THEN_LOSS':58,'P3_NEVER_PROFITABLE':51,'WINNER':170},
 'B02_2023H2':{'P1_GIVEBACK_TO_LOSS':26,'P2_MINOR_FAVORABLE_THEN_LOSS':19,'P3_NEVER_PROFITABLE':7,'WINNER':57},'F05_2023H2':{'P1_GIVEBACK_TO_LOSS':79,'P2_MINOR_FAVORABLE_THEN_LOSS':71,'P3_NEVER_PROFITABLE':34,'WINNER':179},
 'B02_2024H1':{'P1_GIVEBACK_TO_LOSS':16,'P2_MINOR_FAVORABLE_THEN_LOSS':18,'P3_NEVER_PROFITABLE':6,'WINNER':57},'F05_2024H1':{'P1_GIVEBACK_TO_LOSS':48,'P2_MINOR_FAVORABLE_THEN_LOSS':64,'P3_NEVER_PROFITABLE':41,'WINNER':178},
 'B02_2024H2':{'P1_GIVEBACK_TO_LOSS':22,'P2_MINOR_FAVORABLE_THEN_LOSS':9,'P3_NEVER_PROFITABLE':7,'WINNER':64},'F05_2024H2':{'P1_GIVEBACK_TO_LOSS':108,'P2_MINOR_FAVORABLE_THEN_LOSS':34,'P3_NEVER_PROFITABLE':50,'WINNER':200}}
 assert counts==expected_counts,(counts,expected_counts)
 tw=trades.copy()
 for c in ['signal_utc','entry_utc','close_utc']: tw[c]=zfmt(tw[c])
 tw['entry_bid']=tw.entry_bid.map(lambda x:f'{float(x):.3f}');tw['realized_pl_jpy']=tw.realized_pl_jpy.round().astype(int)
 trade_bytes=tw.to_csv(index=False,lineterminator='\n').encode('utf-8'); trade_path=a.out_dir/'usdjpy_b02_f05_source_trade_ledger_v2.csv';trade_path.write_bytes(trade_bytes)
 sw=states.copy();sw['observation_utc']=zfmt(sw.observation_utc);state_bytes=sw.to_csv(index=False,lineterminator='\n',na_rep='',float_format='%.8f').encode('utf-8');state_gz=deterministic_gzip(state_bytes);state_path=a.out_dir/'usdjpy_b02_f05_entry_exit_state_ledger_v2.csv.gz';state_path.write_bytes(state_gz)
 receipt={'schema_version':'usdjpy_b02_f05_hyp024_input_materialization_v2','status':'PASS_NO_OUTCOMES','source_sha256':actual,'trade_rows':len(tw),'trade_id_count':states.trade_id.nunique(),'state_rows':len(sw),'path_class_counts':expected_counts,'trades_path':trade_path.name,'trades_sha256':sha256_file(trade_path),'states_path':state_path.name,'states_sha256':sha256_file(state_path),'state_uncompressed_sha256':hashlib.sha256(state_bytes).hexdigest(),'outcomes_computed':False,'indicator_contract':{'price_series':'M15 executable bid open','momentum':'side*(open-open.shift(4))/0.01','ema20':'pandas ewm(span=20,adjust=False)','macd':'pandas ewm spans 12/26 and signal 9, adjust=False','observation':'entry through baseline close inclusive','executable_pips':'round(side*(bid_open-entry_bid)/0.01-0.5,1)'},'historical_2024_mutated':False,'2025_accessed':False}
 (a.out_dir/'usdjpy_b02_f05_hyp024_input_materialization_v2.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 print(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True))
if __name__=='__main__':main()

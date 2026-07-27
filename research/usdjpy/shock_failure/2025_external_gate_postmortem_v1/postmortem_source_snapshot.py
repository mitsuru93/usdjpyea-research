#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, gzip, hashlib, json, math, os, re
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, wasserstein_distance

PIP=0.01
JPY_PER_PIP=10.0
CANDIDATE='B_EXECUTABLE_T0_8BAR'
FOLDS=['2023H1','2023H2','2024H1','2024H2','2025H1','2025H2']
ORACLE='ORACLE_DIAGNOSTIC_NOT_IMPLEMENTABLE_CANDIDATE'


def args():
 p=argparse.ArgumentParser()
 p.add_argument('--phase2-dir',type=Path,required=True)
 p.add_argument('--p6-root',type=Path)
 p.add_argument('--mt4-context-dir',type=Path)
 p.add_argument('--raw-2025-root',type=Path,required=True)
 p.add_argument('--corrected-p6',type=Path,required=True)
 p.add_argument('--out-dir',type=Path,required=True)
 p.add_argument('--research-sha',default='UNKNOWN')
 p.add_argument('--core-sha',default='UNKNOWN')
 p.add_argument('--run-id',default='LOCAL')
 return p.parse_args()

def sha256(p:Path):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()

def write_json(p,obj):p.write_text(json.dumps(clean(obj),indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')
def clean(v):
 if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [clean(x) for x in v]
 if isinstance(v,(np.integer,)):return int(v)
 if isinstance(v,(np.floating,float)):return None if not np.isfinite(v) else float(v)
 if isinstance(v,(np.bool_,bool)):return bool(v)
 if isinstance(v,pd.Timestamp):return v.isoformat()
 return v

def pf(vals):
 s=pd.Series(vals,dtype=float);gp=s[s>0].sum();gl=-s[s<0].sum();return None if gl<=0 else float(gp/gl)
def session(ts):
 h=pd.Timestamp(ts).hour
 return 'TOKYO' if h<7 else ('LONDON' if h<12 else ('LONDON_NY_OVERLAP' if h<16 else ('NEW_YORK' if h<21 else 'TRANSITION')))
def fold(ts):
 t=pd.Timestamp(ts)
 return f'{t.year}H{1 if t.month<=6 else 2}'

def read_csv_robust(p):
 raw=Path(p).read_bytes()
 for enc in ('utf-8-sig','cp932','cp1252','latin-1'):
  try:return pd.read_csv(pd.io.common.BytesIO(raw),encoding=enc)
  except UnicodeDecodeError:pass
 raise RuntimeError(p)
def detail(v):
 d={}
 for x in str(v).split(';'):
  if '=' in x:
   k,z=x.split('=',1);d[k.strip()]=z.strip()
 return d

def locate(root,name):
 q=list(Path(root).rglob(name))
 if len(q)!=1:raise RuntimeError(f'{name} count={len(q)} under {root}')
 return q[0]

class TickStore:
 def __init__(self,root):
  self.root=Path(root);self.files={};self.cache={}
  for p in self.root.rglob('*.csv.gz'):
   parts=p.parts
   found=None
   for i in range(len(parts)-4):
    if re.fullmatch(r'20\d{2}',parts[i]) and re.fullmatch(r'\d{2}',parts[i+1]) and re.fullmatch(r'\d{2}',parts[i+2]) and re.fullmatch(r'\d{2}\.csv\.gz',parts[i+3]):
     found=(int(parts[i]),int(parts[i+1]),int(parts[i+2]),int(parts[i+3][:2]));break
   if found:self.files[found]=p
  if len(self.files)<8000:raise RuntimeError(f'2025 hourly tick files indexed={len(self.files)}')
 def hour(self,t):
  h=pd.Timestamp(t).tz_convert('UTC').floor('h');k=(h.year,h.month,h.day,h.hour)
  if k in self.cache:return self.cache[k]
  p=self.files.get(k)
  if not p:
   d=pd.DataFrame(columns=['timestamp_utc','bid','ask'])
  else:
   d=pd.read_csv(p,usecols=['timestamp_utc','bid','ask'])
   d['timestamp_utc']=pd.to_datetime(d.timestamp_utc,utc=True,format='mixed')
   d=d.sort_values('timestamp_utc').drop_duplicates('timestamp_utc').reset_index(drop=True)
  self.cache[k]=d;return d
 def between(self,start,end,include_end=False):
  s=pd.Timestamp(start).tz_convert('UTC');e=pd.Timestamp(end).tz_convert('UTC');frames=[]
  for h in pd.date_range(s.floor('h'),e.floor('h'),freq='h'):
   q=self.hour(h)
   if len(q):frames.append(q)
  if not frames:return pd.DataFrame(columns=['timestamp_utc','bid','ask'])
  z=pd.concat(frames,ignore_index=True).sort_values('timestamp_utc').drop_duplicates('timestamp_utc')
  mask=(z.timestamp_utc>=s)&(z.timestamp_utc<=e if include_end else z.timestamp_utc<e)
  return z[mask].reset_index(drop=True)
 def first(self,t,max_wait='8h'):
  z=self.between(t,pd.Timestamp(t)+pd.Timedelta(max_wait),True);return None if z.empty else z.iloc[0]
 def build_m15(self):
  rows=[]
  for k,p in sorted(self.files.items()):
   y,m,d,h=k
   # stream one hour and form four 15-minute bars without materializing full year ticks
   buckets={}
   with gzip.open(p,'rt',encoding='utf-8',newline='') as f:
    for r in csv.DictReader(f):
     t=pd.Timestamp(r['timestamp_utc']);q=t.minute//15;bid=float(r['bid']);ask=float(r['ask'])
     b=buckets.get(q)
     if b is None:buckets[q]={'time':t.floor('15min'),'open':bid,'high':bid,'low':bid,'close':bid,'first_tick':t,'last_tick':t,'ticks':1,'spread_sum':(ask-bid)/PIP,'spread_max':(ask-bid)/PIP}
     else:
      b['high']=max(b['high'],bid);b['low']=min(b['low'],bid);b['close']=bid;b['last_tick']=t;b['ticks']+=1;b['spread_sum']+=(ask-bid)/PIP;b['spread_max']=max(b['spread_max'],(ask-bid)/PIP)
   for b in buckets.values():b['mean_spread_pips']=b.pop('spread_sum')/b['ticks'];rows.append(b)
  x=pd.DataFrame(rows).sort_values('time').drop_duplicates('time').reset_index(drop=True)
  x['time']=pd.to_datetime(x.time,utc=True)
  return x

def add_features(x):
 x=x.copy();pc=x.close.shift();x['tr_pips']=pd.concat([x.high-x.low,(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)/PIP
 x['body_pips']=(x.close-x.open).abs()/PIP;x['median_tr96']=x.tr_pips.rolling(96).median();x['shock_ratio']=x.tr_pips/x.median_tr96
 pos=(x.close-x.low)/(x.high-x.low).replace(0,np.nan);direction=np.sign(x.close-x.open)
 x['up_shock']=(x.tr_pips>=2.5*x.median_tr96)&(x.body_pips>=.65*x.tr_pips)&(direction>0)&(pos>=.8)
 x['down_shock']=(x.tr_pips>=2.5*x.median_tr96)&(x.body_pips>=.65*x.tr_pips)&(direction<0)&(pos<=.2)
 # prior-observable regime features
 x['atr14_pips']=x.tr_pips.rolling(14).mean()
 x['atr_percentile_20d']=x.atr14_pips.rolling(1920,min_periods=200).apply(lambda a: float(pd.Series(a).rank(pct=True).iloc[-1]),raw=False)
 ret=x.close.diff();x['directional_autocorr_16']=ret.rolling(16).apply(lambda a: pd.Series(a).autocorr(1),raw=False)
 x['persistence_16']=np.sign(ret).rolling(16).mean().abs()
 h1=x.set_index('time').close.resample('1h').last().dropna().to_frame('close');h1['ema20']=h1.close.ewm(span=20,adjust=False).mean();h1['ema50']=h1.close.ewm(span=50,adjust=False).mean()
 h4=x.set_index('time').close.resample('4h').last().dropna().to_frame('close');h4['ema20']=h4.close.ewm(span=20,adjust=False).mean();h4['ema50']=h4.close.ewm(span=50,adjust=False).mean()
 x=pd.merge_asof(x.sort_values('time'),h1.reset_index().rename(columns={'close':'h1_close','ema20':'h1_ema20','ema50':'h1_ema50'}),on='time',direction='backward')
 x=pd.merge_asof(x.sort_values('time'),h4.reset_index().rename(columns={'close':'h4_close','ema20':'h4_ema20','ema50':'h4_ema50'}),on='time',direction='backward')
 x['h1_trend_state']=np.where(x.h1_ema20>x.h1_ema50,'UP',np.where(x.h1_ema20<x.h1_ema50,'DOWN','FLAT'))
 x['h4_trend_state']=np.where(x.h4_ema20>x.h4_ema50,'UP',np.where(x.h4_ema20<x.h4_ema50,'DOWN','FLAT'))
 return x

def reproduce_raw_events(x):
 rows=[];mid=(x.high.shift()+x.low.shift())/2
 for i in x.index[(x.up_shock.shift(fill_value=False))&(x.close<mid)&(x.close<x.open)]:rows.append((int(i),-1,'up_shock_failed'))
 for i in x.index[(x.down_shock.shift(fill_value=False))&(x.close>mid)&(x.close>x.open)]:rows.append((int(i),1,'down_shock_failed'))
 rows.sort();keep=[];active=-1
 for i,side,reason in rows:
  e=i+1;q=e+8
  if i<100 or q>=len(x) or fold(x.time.iloc[e])!=fold(x.time.iloc[q]) or i<=active:continue
  keep.append({'failure_i':i,'shock_i':i-1,'entry_i':e,'exit_i':q,'side':side,'reason':reason});active=i+9
 out=[]
 for r in keep:
  s=x.iloc[r['shock_i']];f=x.iloc[r['failure_i']];e=x.iloc[r['entry_i']];q=x.iloc[r['exit_i']]
  out.append({**r,'event_id':f"{fold(e.time)}|D_SHOCK_FAILURE|{e.time.isoformat()}|{r['side']}",'fold':fold(e.time),'shock_utc':s.time,'failure_utc':f.time,'decision_utc':e.time,'exit_boundary':q.time,'shock_tr_pips':s.tr_pips,'median_tr96':s.median_tr96,'shock_ratio':s.shock_ratio,'shock_body_pips':s.body_pips,'shock_midpoint':(s.high+s.low)/2,'failure_close':f.close,'atr14_pips':e.atr14_pips,'atr_percentile_20d':e.atr_percentile_20d,'directional_autocorr_16':e.directional_autocorr_16,'persistence_16':e.persistence_16,'h1_trend_state':e.h1_trend_state,'h4_trend_state':e.h4_trend_state})
 return pd.DataFrame(out)

def lifecycle(store,event):
 decision=pd.Timestamp(event['decision_utc']);side=int(event['side']);ent=store.first(decision);ex=store.first(decision+pd.Timedelta('120m'))
 if ent is None or ex is None:return {'data_anomaly':True,'anomaly':'missing executable tick'}
 path=store.between(ent.timestamp_utc,decision+pd.Timedelta('240m'),True)
 if path.empty:return {'data_anomaly':True,'anomaly':'empty lifecycle'}
 if side>0:
  net=(path.bid-float(ent.ask))/PIP;gross=(path.bid-float(ent.bid))/PIP
 else:
  net=(float(ent.bid)-path.ask)/PIP;gross=(float(ent.ask)-path.ask)/PIP
 path=path.assign(net_pips=net,gross_pips=gross)
 before=path[path.timestamp_utc<=decision+pd.Timedelta('120m')];after=path[(path.timestamp_utc>decision+pd.Timedelta('120m'))&(path.timestamp_utc<=decision+pd.Timedelta('240m'))]
 mfe_i=before.net_pips.idxmax();mae_i=before.net_pips.idxmin();first=before[before.net_pips>0]
 fixed={}
 for mins in [30,60,90,120,180]:
  row=store.first(decision+pd.Timedelta(minutes=mins));fixed[f'pnl_{mins}m_pips']=None if row is None else ((float(row.bid)-float(ent.ask))/PIP if side>0 else (float(ent.bid)-float(row.ask))/PIP)
 pnl120=fixed['pnl_120m_pips'];mfe=float(before.net_pips.max());mae=float(before.net_pips.min());gross_mfe=float(before.gross_pips.max())
 first_time=None if first.empty else float((first.timestamp_utc.iloc[0]-ent.timestamp_utc).total_seconds()/60)
 time_mfe=float((before.loc[mfe_i,'timestamp_utc']-ent.timestamp_utc).total_seconds()/60);time_mae=float((before.loc[mae_i,'timestamp_utc']-ent.timestamp_utc).total_seconds()/60)
 post120_mfe=None if after.empty else float(after.net_pips.max())
 raw_failure_close=float(event.get('failure_close',np.nan));exit_quote=float(ex.bid if side>0 else ex.ask)
 if mfe>0 and (pnl120 is not None and pnl120<=0):
  continuation=(side>0 and np.isfinite(raw_failure_close) and exit_quote<raw_failure_close) or (side<0 and np.isfinite(raw_failure_close) and exit_quote>raw_failure_close)
  klass='F_CONTINUATION_RESUMPTION' if continuation else 'D_PROFIT_THEN_GIVEBACK'
 elif mfe<=0 and gross_mfe<=0:klass='A_IMMEDIATE_SIGNAL_FAILURE'
 elif mfe<=0 and gross_mfe>0:klass='C_INSUFFICIENT_REVERSAL'
 elif (pnl120 is None or pnl120<=0) and post120_mfe is not None and post120_mfe>0:klass='E_TIMEOUT_TRUNCATION'
 elif pnl120 is not None and pnl120>0 and first_time is not None and first_time>60:klass='B_DELAYED_REVERSAL'
 else:klass='H_RETAINED_REVERSAL'
 return {'data_anomaly':False,'entry_execution_time':ent.timestamp_utc,'entry_bid_raw':float(ent.bid),'entry_ask_raw':float(ent.ask),'entry_spread_pips_raw':float((ent.ask-ent.bid)/PIP),'exit_execution_time_raw':ex.timestamp_utc,'exit_bid_raw':float(ex.bid),'exit_ask_raw':float(ex.ask),'pnl_120m_pips_raw':pnl120,'mfe_pips':mfe,'mae_pips':mae,'gross_mfe_pips':gross_mfe,'time_to_mfe_min':time_mfe,'time_to_mae_min':time_mae,'first_profitable_time_min':first_time,'profitable_at_any_time':bool(mfe>0),'profitable_before_120m':bool(mfe>0),'profit_giveback_pips':None if pnl120 is None else mfe-pnl120,'post120_to_240_mfe_pips':post120_mfe,'classification':klass,**fixed,'oracle_mfe_exit_pips':mfe,'oracle_first_profit_exit_pips':None if first.empty else float(first.net_pips.iloc[0]),'oracle_delayed_reversal_capture_pips':post120_mfe,'oracle_label':ORACLE}

def mt4_events(root):
 rows=[]
 for h in ['h1','h2']:
  p=locate(root,f'sf_2025{h}_standalone.csv');d=read_csv_robust(p)
  opens=d[d.event=='order_opened'].copy();closes=d[d.event=='order_closed'].copy();cm={int(r.ticket):r for r in closes.itertuples()}
  base=read_csv_robust(locate(root,f'base_2025{h}_baseline.csv'))
  bo=base[base.event=='order_opened'].copy();bc=base[base.event=='order_closed'].copy();bcm={int(r.ticket):r for r in bc.itertuples()}
  btr=[]
  for r in bo.itertuples():
   c=bcm.get(int(r.ticket));btr.append({'strategy':r.strategy,'side':int(r.side),'entry':pd.to_datetime(r.entry_utc.replace('.','-'),utc=True),'close':pd.to_datetime(c.utc_time.replace('.','-'),utc=True) if c is not None else pd.Timestamp.max.tz_localize('UTC'),'pnl':float(c.gross_pips)*JPY_PER_PIP if c is not None else 0.})
  for r in opens.itertuples():
   c=cm[int(r.ticket)];dec=pd.to_datetime(r.decision_utc.replace('.','-'),utc=True);shock=pd.to_datetime(r.shock_utc.replace('.','-'),utc=True);fail=pd.to_datetime(r.failure_utc.replace('.','-'),utc=True);det=detail(r.detail)
   active=[x for x in btr if x['entry']<dec+pd.Timedelta('120m') and x['close']>dec]
   day=[x for x in btr if x['close'].strftime('%Y-%m-%d')==dec.strftime('%Y-%m-%d')]
   rows.append({'event_id':f"{fold(dec)}|D_SHOCK_FAILURE|{dec.isoformat()}|{int(r.side)}",'half':fold(dec),'month':dec.strftime('%Y-%m'),'day':dec.strftime('%Y-%m-%d'),'side':int(r.side),'side_label':'LONG' if int(r.side)>0 else 'SHORT','session':session(dec),'shock_utc':shock,'failure_utc':fail,'decision_utc':dec,'mt4_entry_time':pd.to_datetime(r.utc_time.replace('.','-'),utc=True),'mt4_entry_price':float(r.price),'mt4_exit_time':pd.to_datetime(c.utc_time.replace('.','-'),utc=True),'mt4_exit_price':float(c.price),'mt4_pnl_pips':float(c.gross_pips),'shock_tr_pips_mt4':float(det['tr']),'median96_mt4':float(det['median96']),'shock_ratio_mt4':float(det['tr'])/float(det['median96']),'shock_midpoint_mt4':float(det['mid']),'b02_overlap':any(x['strategy']=='B02' for x in active),'f05_overlap':any(x['strategy']=='F05' for x in active),'same_direction_exposure':any(x['side']==int(r.side) for x in active),'opposite_direction_exposure':any(x['side']!=int(r.side) for x in active),'simultaneous_baseline_positions':len(active),'baseline_daily_pnl_jpy':sum(x['pnl'] for x in day),'runtime_execution_errors':0})
 return pd.DataFrame(rows)

def mt4_events_from_context(root):
 rows=[];authority=None
 for p in sorted(Path(root).glob('mt4_events_*.json')):
  x=json.loads(p.read_text(encoding='utf-8'));authority=authority or x.get('authority');rows.extend(x.get('events',[]))
 if len(rows)!=47:raise RuntimeError(f'mt4 context events={len(rows)}')
 d=pd.DataFrame(rows)
 for c in ['shock_utc','failure_utc','decision_utc','mt4_entry_time','mt4_exit_time']:
  d[c]=pd.to_datetime(d[c],utc=True)
 d.attrs['authority']=authority or {}
 return d

def summary(g):
 s=g.pnl_jpy.astype(float);return {'trades':len(g),'net_jpy':float(s.sum()),'pf':pf(s),'win_rate':float((s>0).mean()) if len(g) else None,'median_jpy':float(s.median()) if len(g) else None,'mean_mfe_pips':float(g.mfe_pips.mean()) if 'mfe_pips' in g else None,'mean_mae_pips':float(g.mae_pips.mean()) if 'mae_pips' in g else None}
def slices(df,cols):
 out=[]
 for keys,g in df.groupby(cols,dropna=False):
  if not isinstance(keys,tuple):keys=(keys,)
  r=summary(g);r.update(dict(zip(cols,keys)));out.append(r)
 return pd.DataFrame(out)
def concentration(g):
 rows=[]
 def add(name,z):r=summary(z);r['scenario']=name;rows.append(r)
 add('BASELINE',g);s=g.sort_values('pnl_jpy')
 for n in [1,3,5]:add(f'WORST_{n}_TRADES_REMOVED',s.iloc[n:])
 day=g.groupby('day').pnl_jpy.sum();mon=g.groupby('month').pnl_jpy.sum()
 add('WORST_DAY_REMOVED',g[g.day!=day.idxmin()]);add('WORST_MONTH_REMOVED',g[g.month!=mon.idxmin()])
 for v in g.side_label.unique():add(f'SIDE_{v}_REMOVED',g[g.side_label!=v])
 for v in g.session.unique():add(f'SESSION_{v}_REMOVED',g[g.session!=v])
 return pd.DataFrame(rows)
def shift(a,b,features):
 rows=[]
 for f in features:
  x=pd.to_numeric(a[f],errors='coerce').dropna();y=pd.to_numeric(b[f],errors='coerce').dropna()
  if len(x)<2 or len(y)<2:continue
  pooled=math.sqrt(((len(x)-1)*x.var(ddof=1)+(len(y)-1)*y.var(ddof=1))/(len(x)+len(y)-2)) if len(x)+len(y)>2 else np.nan
  rows.append({'feature':f,'historical_n':len(x),'2025_n':len(y),'historical_mean':x.mean(),'2025_mean':y.mean(),'standardized_mean_difference':None if not pooled or not np.isfinite(pooled) else (y.mean()-x.mean())/pooled,'ks_statistic':ks_2samp(x,y).statistic,'wasserstein_distance':wasserstein_distance(x,y)})
 return pd.DataFrame(rows)

def main():
 a=args();out=a.out_dir;out.mkdir(parents=True,exist_ok=True)
 phase=read_csv_robust(locate(a.phase2_dir,'candidate_trade_ledger.csv.gz'));hist=phase[(phase.candidate_id==CANDIDATE)&phase.admitted.fillna(False)].copy();hist['entry_utc']=pd.to_datetime(hist.entry_utc,utc=True);hist['exit_utc']=pd.to_datetime(hist.exit_utc,utc=True);hist['month']=hist.entry_utc.dt.strftime('%Y-%m');hist['day']=hist.entry_utc.dt.strftime('%Y-%m-%d');hist['pnl_jpy']=hist.pnl_jpy.astype(float)
 store=TickStore(a.raw_2025_root);bars=add_features(store.build_m15());raw_events=reproduce_raw_events(bars);mt=mt4_events_from_context(a.mt4_context_dir) if a.mt4_context_dir else mt4_events(a.p6_root)
 # attach raw features at same MT4 decision times and lifecycle
 idx=bars.set_index('time');led=[]
 for r in mt.to_dict('records'):
  row=idx.loc[r['decision_utc']] if r['decision_utc'] in idx.index else None
  if row is not None:r.update({'atr14_pips':row.atr14_pips,'atr_percentile_20d':row.atr_percentile_20d,'directional_autocorr_16':row.directional_autocorr_16,'persistence_16':row.persistence_16,'h1_trend_state':row.h1_trend_state,'h4_trend_state':row.h4_trend_state})
  match=raw_events[(raw_events.decision_utc==r['decision_utc'])&(raw_events.side==r['side'])]
  r['raw_signal_identity_match']=len(match)==1
  if len(match):
   m=match.iloc[0];r.update({'shock_tr_pips_raw':m.shock_tr_pips,'median96_raw':m.median_tr96,'shock_ratio_raw':m.shock_ratio,'shock_midpoint_raw':m.shock_midpoint,'failure_close':m.failure_close})
  else:r.update({'shock_tr_pips_raw':np.nan,'median96_raw':np.nan,'shock_ratio_raw':np.nan,'shock_midpoint_raw':np.nan,'failure_close':np.nan})
  r.update(lifecycle(store,r));r['pnl_jpy']=r['mt4_pnl_pips']*JPY_PER_PIP;led.append(r)
 led=pd.DataFrame(led);led.to_csv(out/'2025_event_ledger.csv.gz',index=False,compression='gzip')
 # pure raw event performance
 raw_led=[]
 for r in raw_events.to_dict('records'):
  z={**r,**lifecycle(store,r)};z['pnl_jpy']=z.get('pnl_120m_pips_raw',np.nan)*JPY_PER_PIP;raw_led.append(z)
 raw_led=pd.DataFrame(raw_led);raw_led.to_csv(out/'2025_raw_source_event_ledger.csv.gz',index=False,compression='gzip')
 # historical normalized table
 hist2=hist.rename(columns={'fold':'half'}).copy();hist2['classification']=np.where(hist2.pnl_jpy>0,'H_RETAINED_REVERSAL',np.where(hist2.mfe_pips>0,'D_PROFIT_THEN_GIVEBACK','A_IMMEDIATE_SIGNAL_FAILURE'))
 hist2['atr14_pips']=np.nan;hist2['atr_percentile_20d']=np.nan;hist2['directional_autocorr_16']=np.nan;hist2['persistence_16']=np.nan
 combined=pd.concat([hist2,led],ignore_index=True,sort=False)
 slices(combined,['half']).to_csv(out/'fold_comparison.csv',index=False)
 slices(combined,['half','side_label']).to_csv(out/'side_comparison.csv',index=False)
 slices(combined,['half','session']).to_csv(out/'session_comparison.csv',index=False)
 slices(led,['classification']).to_csv(out/'signal_exit_classification.csv',index=False)
 slices(led,['side_label']).to_csv(out/'2025_side_comparison.csv',index=False)
 slices(led,['session']).to_csv(out/'2025_session_comparison.csv',index=False)
 slices(led,['month']).to_csv(out/'2025_month_comparison.csv',index=False)
 concentration(led).to_csv(out/'concentration_report.csv',index=False)
 oracle_cols=['event_id','half','side_label','session','month','pnl_30m_pips','pnl_60m_pips','pnl_90m_pips','pnl_120m_pips','pnl_180m_pips','oracle_mfe_exit_pips','oracle_first_profit_exit_pips','oracle_delayed_reversal_capture_pips','oracle_label']
 led.rename(columns={'pnl_120m_pips_raw':'pnl_120m_pips'})[[c for c in oracle_cols if c in led.rename(columns={'pnl_120m_pips_raw':'pnl_120m_pips'}).columns]].to_csv(out/'oracle_exit_diagnostics.csv',index=False)
 lifecycle_cols=['event_id','classification','mfe_pips','mae_pips','time_to_mfe_min','time_to_mae_min','first_profitable_time_min','profitable_at_any_time','profitable_before_120m','profit_giveback_pips','post120_to_240_mfe_pips']
 led[lifecycle_cols].to_csv(out/'mfe_mae_lifecycle_analysis.csv',index=False)
 # shift tables and bootstrap
 features=['shock_ratio','shock_tr_pips','mfe_pips','mae_pips','pnl_jpy','observed_spread_entry_pips']
 h=hist.rename(columns={'shock_ratio':'shock_ratio','shock_tr_pips':'shock_tr_pips'});y=led.rename(columns={'shock_ratio_mt4':'shock_ratio','shock_tr_pips_mt4':'shock_tr_pips','entry_spread_pips_raw':'observed_spread_entry_pips'})
 sh=shift(h,y,features);sh.to_csv(out/'distribution_shift_metrics.csv',index=False)
 rng=np.random.default_rng(20260727);vals=led.pnl_jpy.to_numpy();boots=np.array([rng.choice(vals,len(vals),replace=True).sum() for _ in range(10000)])
 distribution={'event_frequency':{'2023':int((hist.entry_utc.dt.year==2023).sum()),'2024':int((hist.entry_utc.dt.year==2024).sum()),'2025_mt4':len(led),'2025_raw_source':len(raw_led)},'mt4_vs_raw_identity':{'mt4_events':len(led),'matched':int(led.raw_signal_identity_match.sum()),'recall':float(led.raw_signal_identity_match.mean()),'raw_events':len(raw_led)},'bootstrap_2025_net_ci95_jpy':[float(np.quantile(boots,.025)),float(np.quantile(boots,.975))],'bootstrap_probability_positive':float((boots>0).mean()),'feature_shift_file':'distribution_shift_metrics.csv'};write_json(out/'distribution_shift_report.json',distribution)
 # portfolio interaction
 cp6=json.loads(a.corrected_p6.read_text());daily_sf=led.groupby('day').pnl_jpy.sum();portfolio={}
 for h in ['h1','h2']:
  q=led[led.half==f'2025{h.upper()}'];base=cp6['halves'][h]['baseline_risk'];integ=cp6['halves'][h]['integrated_risk'];portfolio[h]={'baseline_final_equity_jpy':base['final_equity_jpy'],'integrated_final_equity_jpy':integ['final_equity_jpy'],'equity_change_jpy':integ['final_equity_jpy']-base['final_equity_jpy'],'baseline_mdd_jpy':base['maximum_equity_drawdown_jpy'],'integrated_mdd_jpy':integ['maximum_equity_drawdown_jpy'],'mdd_change_jpy':integ['maximum_equity_drawdown_jpy']-base['maximum_equity_drawdown_jpy'],'shock_net_jpy':q.pnl_jpy.sum(),'b02_overlap_rate':q.b02_overlap.mean(),'f05_overlap_rate':q.f05_overlap.mean(),'same_direction_overlap_rate':q.same_direction_exposure.mean(),'opposite_direction_overlap_rate':q.opposite_direction_exposure.mean(),'negative_baseline_day_rate':(q.baseline_daily_pnl_jpy<0).mean(),'stopout':integ['stopout_breached']}
 write_json(out/'portfolio_interaction_report.json',portfolio)
 # decision logic: integrity is sufficient only when raw source coverage/identity are reported; fixed candidate definitely failed.
 matched=float(led.raw_signal_identity_match.mean());profitable=float(led.profitable_before_120m.mean());giveback=float(led.classification.isin(['D_PROFIT_THEN_GIVEBACK','F_CONTINUATION_RESUMPTION']).mean());immediate=float(led.classification.eq('A_IMMEDIATE_SIGNAL_FAILURE').mean());timeout=float(led.classification.eq('E_TIMEOUT_TRUNCATION').mean())
 if matched<0.70:decision='DATA_OR_EXECUTION_INTEGRITY_BLOCKED'
 elif giveback>immediate and profitable>=0.50:decision='SHOCK_FAILURE_EXIT_LIFECYCLE_FAILED'
 elif immediate>=0.40 and profitable<0.50:decision='SHOCK_FAILURE_SIGNAL_MECHANISM_FAILED'
 else:decision='CURRENT_FIXED_CANDIDATE_EXTERNAL_PORTABILITY_FAILED_FAMILY_RETAINED'
 final={'schema_version':'usdjpy_shock_failure_2025_external_gate_postmortem_final_v1','candidate_id':CANDIDATE,'decision':decision,'fixed_candidate_status':'REJECTED_FOR_PRODUCTION_AND_PORTABLE_CORE_ADOPTION','family_status':'RETAIN_FOR_NEW_HYPOTHESIS_RESEARCH_ONLY' if decision!='SHOCK_FAILURE_FAMILY_REJECTED' else 'REJECTED','no_retuning':True,'2025_consumed':True,'2025_reusable_as_holdout':False,'next_external_period':'first complete unused period after 2025, provisionally 2026 only after the new candidate is preregistered without 2025 selection','diagnostics':{'raw_identity_match_rate':matched,'profitable_before_120m_rate':profitable,'giveback_or_continuation_rate':giveback,'immediate_failure_rate':immediate,'timeout_truncation_rate':timeout,'mt4_combined_net_jpy':float(led.pnl_jpy.sum()),'mt4_pf':pf(led.pnl_jpy),'raw_source_event_net_jpy':float(raw_led.pnl_jpy.sum()),'raw_source_event_pf':pf(raw_led.pnl_jpy)},'research_sha':a.research_sha,'core_sha':a.core_sha,'run_id':a.run_id};write_json(out/'final_decision.json',final)
 # regime summary
 regime=slices(led,['h1_trend_state','h4_trend_state']);regime.to_csv(out/'regime_comparison.csv',index=False)
 report=f'''# USDJPY Shock Failure 2025 External-Gate Failure Postmortem\n\n## Decision\n`{decision}`\n\nThe fixed candidate `B_EXECUTABLE_T0_8BAR` remains failed for portable adoption. No parameter, direction, session, threshold, failure rule, entry timing, timeout, spread, Bid/Ask convention or B02/F05 semantic was changed.\n\n## Evidence integrity\n- P6 MT4 events: {len(led)}\n- 2025 Dukascopy raw-source events: {len(raw_led)}\n- MT4 events reproduced by raw source at identical decision time and side: {int(led.raw_signal_identity_match.sum())}/{len(led)} ({matched:.1%})\n- Runtime/execution anomaly rows: {int(led.data_anomaly.sum())}\n\n## Fixed-candidate outcome\n- Net: {led.pnl_jpy.sum():.0f} JPY\n- PF: {pf(led.pnl_jpy):.3f}\n- Profitable before 120m: {profitable:.1%}\n- Immediate signal failure: {immediate:.1%}\n- Profit giveback or continuation resumption: {giveback:.1%}\n- Timeout truncation: {timeout:.1%}\n\n## Boundaries\nAll alternative exits are labelled `{ORACLE}` and are diagnostic only. 2025 is consumed and cannot be used to select a replacement candidate. Any replacement requires a new hypothesis ID, candidate ID and preregistration based on 2023H1–2024H2, with a genuinely unused future external period.\n''';(out/'human_readable_report.md').write_text(report,encoding='utf-8')
 # source inventory, reproduce, manifest
 inv={'schema_version':'usdjpy_shock_failure_2025_postmortem_source_inventory_v1','phase2_ledger':{'path':str(locate(a.phase2_dir,'candidate_trade_ledger.csv.gz')),'sha256':sha256(locate(a.phase2_dir,'candidate_trade_ledger.csv.gz'))},'corrected_p6':{'path':str(a.corrected_p6),'sha256':sha256(a.corrected_p6)},'raw_2025_hour_files':len(store.files),'p6_source_root':str(a.p6_root) if a.p6_root else None,'mt4_context_dir':str(a.mt4_context_dir) if a.mt4_context_dir else None,'research_sha':a.research_sha,'core_sha':a.core_sha};write_json(out/'source_inventory.json',inv)
 (out/'REPRODUCE.md').write_text(f"# Reproduction\n\nRun `.github/workflows/usdjpy_shock_failure_2025_postmortem_v1.yml` on the frozen branch. The workflow downloads the immutable Phase 2 Release, corrected Core P6 Release, and immutable 2025 raw Bid/Ask Tick Release, then runs:\n\n```bash\npython tools/run_usdjpy_shock_failure_2025_postmortem_v1.py --phase2-dir PHASE2 --mt4-context-dir research_inputs/usdjpy/shock_failure/2025_postmortem_v1 --raw-2025-root RAW --corrected-p6 corrected_p6_result.json --out-dir OUT\n```\n",encoding='utf-8')
 files=[]
 for p in sorted(out.iterdir()):
  if p.is_file() and p.name not in {'manifest.json','SHA256SUMS'}:files.append({'path':p.name,'bytes':p.stat().st_size,'sha256':sha256(p)})
 write_json(out/'manifest.json',{'schema_version':'usdjpy_shock_failure_2025_postmortem_manifest_v1','files':files})
 with (out/'SHA256SUMS').open('w') as f:
  for p in sorted(out.iterdir()):
   if p.is_file() and p.name!='SHA256SUMS':f.write(f'{sha256(p)}  {p.name}\n')
 print(json.dumps(final,indent=2))

if __name__=='__main__':main()

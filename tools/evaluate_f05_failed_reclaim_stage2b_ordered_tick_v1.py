#!/usr/bin/env python3
from __future__ import annotations
import argparse, gzip, hashlib, io, itertools, json, tarfile
from pathlib import Path
import pandas as pd

PIP=0.01
FOLDS=["2023H1","2023H2","2024H1","2024H2"]

def sha256(p:Path)->str:
 h=hashlib.sha256();
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()

class TickStore:
 def __init__(self,root:Path):
  self.idx={}; self.cache={}
  for a in sorted(root.rglob('usdjpy-20??-??-raw-ticks-v1.tar.gz')):
   with tarfile.open(a,'r:gz') as tf:
    for m in tf.getmembers():
     if m.isfile() and m.name.endswith('.csv.gz') and 'decoded_csv/USDJPY/' in m.name:
      self.idx[m.name.split('decoded_csv/USDJPY/',1)[1]]=(a,m.name)
 def hour(self,h:pd.Timestamp)->pd.DataFrame:
  k=h.tz_convert('UTC').strftime('%Y/%m/%d/%H.csv.gz')
  if k in self.cache:return self.cache[k]
  if k not in self.idx:
   d=pd.DataFrame(columns=['timestamp_utc','bid','ask']);self.cache[k]=d;return d
  a,m=self.idx[k]
  with tarfile.open(a,'r:gz') as tf: raw=gzip.decompress(tf.extractfile(m).read())
  d=pd.read_csv(io.BytesIO(raw),usecols=['timestamp_utc','bid','ask'])
  d.timestamp_utc=pd.to_datetime(d.timestamp_utc,utc=True);d=d.sort_values('timestamp_utc').drop_duplicates('timestamp_utc',keep='last')
  d.bid=d.bid.astype(float);d.ask=d.ask.astype(float)
  if (d.ask<d.bid).any():raise RuntimeError(('negative_spread',k))
  self.cache[k]=d;return d
 def window(self,s,e):
  fs=[self.hour(h) for h in pd.date_range(s.floor('h'),e.floor('h'),freq='h')]
  d=pd.concat(fs,ignore_index=True) if fs else pd.DataFrame()
  return d[(d.timestamp_utc>=s)&(d.timestamp_utc<=e)].sort_values('timestamp_utc') if not d.empty else d

def exec_price(d,side): return d.bid if side==1 else d.ask
def favorable_pips(d,entry,side): return (exec_price(d,side)-entry)*side/PIP
def inside(price,level,side,buf): return price <= level+buf*PIP if side==1 else price >= level-buf*PIP

def bars(ticks,freq):
 x=ticks.set_index('timestamp_utc')[['bid','ask']].resample(freq,label='right',closed='right').last().dropna().reset_index()
 return x

def disarmed(ticks,entry,side,threshold,persistence,end):
 d=ticks[ticks.timestamp_utc<=end].copy()
 if d.empty:return False
 good=favorable_pips(d,entry,side)>=threshold-1e-12
 if persistence=='one_tick':return bool(good.any())
 if persistence=='two_consecutive_ticks':return bool((good & good.shift(fill_value=False)).any())
 if persistence in ('five_seconds','fifteen_seconds'):
  need=5 if persistence=='five_seconds' else 15
  start=None
  for ts,g in zip(d.timestamp_utc,good):
   if g and start is None:start=ts
   if not g:start=None
   if start is not None and (ts-start).total_seconds()>=need:return True
 return False

def trigger_time(ticks,reclaim,baseline_close,level,side,buf,mode):
 d=ticks[(ticks.timestamp_utc>=reclaim)&(ticks.timestamp_utc<baseline_close)]
 if d.empty:return None
 if mode=='next_m5':
  b=bars(d,'5min')
  q=b[b.timestamp_utc>reclaim]
  for r in q.itertuples(index=False):
   if inside(float(r.bid if side==1 else r.ask),level,side,buf):return pd.Timestamp(r.timestamp_utc)
 elif mode=='m1_early':
  b=bars(d,'1min')
  for r in b[b.timestamp_utc>reclaim].itertuples(index=False):
   if inside(float(r.bid if side==1 else r.ask),level,side,buf):return pd.Timestamp(r.timestamp_utc)
 else:
  b=bars(d,'1min');run=0
  for r in b[b.timestamp_utc>reclaim].itertuples(index=False):
   if inside(float(r.bid if side==1 else r.ask),level,side,buf):
    run+=1
    if run>=2:return pd.Timestamp(r.timestamp_utc)
   else:run=0
 return None

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--prereg',required=True);ap.add_argument('--raw-tick-dir',required=True);ap.add_argument('--fixture',required=True);ap.add_argument('--out-dir',required=True);a=ap.parse_args()
 p=json.loads(Path(a.prereg).read_text());out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True)
 assert p['analysis_boundary']['included_periods']==FOLDS and p['analysis_boundary']['excluded_periods']==['2025H1','2025H2']
 store=TickStore(Path(a.raw_tick_dir));fixture=pd.read_csv(a.fixture)
 for c in ['entry_utc','baseline_exit_utc','reclaim_m1_close_utc']:fixture[c]=pd.to_datetime(fixture[c],utc=True)
 axes=p['ordered_tick_axes'];rows=[];ledger=[]
 for sc,thr,pers,conf,delay in itertools.product(p['structural_candidates'],axes['profit_disarm_threshold_executable_pips'],axes['profit_persistence'],axes['failure_confirmation'],axes['exit_delay_seconds']):
  cid=f"buf{sc['close_buffer_pips']}_thr{thr}_{pers}_{conf}_d{delay}"
  fold_delta={f:0.0 for f in FOLDS};stopped=0;winner_damage=0.0;loser_benefit=0.0
  for tr in fixture.itertuples(index=False):
   ticks=store.window(tr.entry_utc,tr.baseline_exit_utc)
   if ticks.empty:raise RuntimeError(('missing_ticks',tr.trade_key))
   trig=trigger_time(ticks,tr.reclaim_m1_close_utc,tr.baseline_exit_utc,float(tr.breakout_level),int(tr.side),float(sc['close_buffer_pips']),conf)
   if trig is None or disarmed(ticks,float(ticks.iloc[0].ask if tr.side==1 else ticks.iloc[0].bid),int(tr.side),float(thr),pers,trig):continue
   target=trig+pd.Timedelta(seconds=int(delay));q=ticks[ticks.timestamp_utc>=target]
   if q.empty or pd.Timestamp(q.iloc[0].timestamp_utc)>=tr.baseline_exit_utc:continue
   px=float(q.iloc[0].bid if tr.side==1 else q.iloc[0].ask);entry=float(ticks.iloc[0].ask if tr.side==1 else ticks.iloc[0].bid)
   cp=(px-entry)*int(tr.side)/PIP;delta=cp-float(tr.baseline_pips);fold_delta[tr.fold]+=delta;stopped+=1
   if float(tr.baseline_pips)>0:winner_damage+=delta
   else:loser_benefit+=delta
   ledger.append({'candidate_id':cid,'trade_key':tr.trade_key,'fold':tr.fold,'trigger_utc':trig.isoformat(),'exit_utc':pd.Timestamp(q.iloc[0].timestamp_utc).isoformat(),'baseline_pips':float(tr.baseline_pips),'candidate_pips':round(cp,4),'delta_pips':round(delta,4)})
  rows.append({'candidate_id':cid,'close_buffer_pips':sc['close_buffer_pips'],'profit_disarm_threshold':thr,'profit_persistence':pers,'failure_confirmation':conf,'exit_delay_seconds':delay,'stopped':stopped,'winner_damage':round(winner_damage,4),'loser_benefit':round(loser_benefit,4),'total':round(sum(fold_delta.values()),4),'min_fold':round(min(fold_delta.values()),4),'positive_folds':sum(v>=-1e-9 for v in fold_delta.values()),**{f:round(v,4) for f,v in fold_delta.items()}})
 grid=pd.DataFrame(rows);grid['all_four_folds_non_negative']=grid.positive_folds.eq(4);grid['winner_damage_abs']=grid.winner_damage.abs();grid=grid.sort_values(['all_four_folds_non_negative','winner_damage_abs','loser_benefit','min_fold','total','stopped'],ascending=[False,True,False,False,False,True],kind='mergesort').reset_index(drop=True);grid.insert(0,'rank',range(1,len(grid)+1))
 grid.to_csv(out/'stage2b_grid_ranked.csv',index=False);pd.DataFrame(ledger).to_csv(out/'stage2b_changed_trade_ledger.csv',index=False)
 top=grid.iloc[0].to_dict();top={k:(v.item() if hasattr(v,'item') else v) for k,v in top.items()}
 result={'schema_version':'1.0','status':'PASS_STAGE2B_ORDERED_TICK_GRID','analysis_periods':FOLDS,'excluded_periods_not_accessed':['2025H1','2025H2'],'grid_candidate_count':len(grid),'selected_candidate':top,'selection_executed':True,'proxy_substitution_used':False,'production_authorization':False}
 (out/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
 manifest={'evaluator_sha256':sha256(Path(__file__)),'prereg_sha256':sha256(Path(a.prereg)),'fixture_sha256':sha256(Path(a.fixture)),'result_sha256':sha256(out/'result.json')};(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=='__main__':main()

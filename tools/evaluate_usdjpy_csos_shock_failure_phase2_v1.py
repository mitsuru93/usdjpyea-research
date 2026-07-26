#!/usr/bin/env python3
from __future__ import annotations
import argparse, gzip, hashlib, io, json, math, tarfile
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd

PIP=0.01
JPYPP=10.0
FOLDS=['2023H1','2023H2','2024H1','2024H2']
ELIGIBLE=['B_EXECUTABLE_T0_8BAR','C_M1_ACCEPTANCE_8BAR','D_EXECUTABLE_T0_4BAR']
ALL_CAND=['A_CSOS_FIXED_BAR']+ELIGIBLE

def sha256_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()

def clean(v):
 if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [clean(x) for x in v]
 if isinstance(v,(bool,np.bool_)):return bool(v)
 if isinstance(v,(np.integer,)):return int(v)
 if isinstance(v,(float,np.floating)):return None if not np.isfinite(v) else float(v)
 if isinstance(v,pd.Timestamp):return v.isoformat()
 return v

def write_json(p:Path,obj):p.write_text(json.dumps(clean(obj),indent=2,ensure_ascii=False,sort_keys=True)+'\n')
def pf(s):
 s=pd.Series(s,dtype=float); gp=s[s>0].sum(); gl=-s[s<0].sum()
 return None if gl<=0 else float(gp/gl)
def maxdd_from_timed(df,time_col='exit_utc',pnl_col='pnl_jpy'):
 if df.empty:return 0.0,0.0
 z=df.sort_values(time_col).reset_index(drop=True); eq=z[pnl_col].cumsum(); peak=eq.cummax(); dd=peak-eq
 m=float(dd.max())
 if m<=0:return 0.0,0.0
 end=dd.idxmax(); peakval=peak.loc[end]; start=eq.loc[:end][eq.loc[:end].eq(peakval)].index[-1]
 after=eq.loc[end:]; rec=after[after>=peakval]
 if len(rec):
  hours=(pd.Timestamp(z.loc[rec.index[0],time_col])-pd.Timestamp(z.loc[start,time_col])).total_seconds()/3600
 else: hours=(pd.Timestamp(z[time_col].max())-pd.Timestamp(z.loc[start,time_col])).total_seconds()/3600
 return m,float(hours)

def session_of(ts):
 h=pd.Timestamp(ts).hour
 return 'TOKYO' if h<7 else ('LONDON' if h<12 else ('LONDON_NY_OVERLAP' if h<16 else ('NEW_YORK' if h<21 else 'TRANSITION')))
def fold_of(ts):
 t=pd.Timestamp(ts)
 return '2023H1' if t<pd.Timestamp('2023-07-01',tz='UTC') else ('2023H2' if t<pd.Timestamp('2024-01-01',tz='UTC') else ('2024H1' if t<pd.Timestamp('2024-07-01',tz='UTC') else '2024H2'))

def load_bars23(p:Path):
 d=pd.read_csv(p); t=pd.to_datetime(d['first_timestamp_mt4_server'],utc=True)
 def sunday(y,m,n,h):
  x=pd.Timestamp(year=y,month=m,day=1,hour=h,tz='UTC'); return x+pd.Timedelta(days=(6-x.weekday())%7+7*(n-1))
 def histutc(z):
  w=z-pd.Timedelta(hours=2); return z-pd.Timedelta(hours=3) if sunday(z.year,3,2,7)<=w<sunday(z.year,11,1,6) else w
 tt=pd.DatetimeIndex([histutc(z) for z in t])
 q=pd.DataFrame({'time':tt,'open':d.open.astype(float),'high':d.high.astype(float),'low':d.low.astype(float),'close':d.close.astype(float)})
 return q[(q.time>=pd.Timestamp('2023-01-01',tz='UTC'))&(q.time<pd.Timestamp('2024-01-01',tz='UTC'))].sort_values('time').drop_duplicates('time').reset_index(drop=True)
def load_bars24(p:Path):
 d=pd.read_csv(p); q=pd.DataFrame({'time':pd.to_datetime(d.time,utc=True),'open':d.bid_open.astype(float),'high':d.bid_high.astype(float),'low':d.bid_low.astype(float),'close':d.bid_close.astype(float)})
 return q[(q.time>=pd.Timestamp('2024-01-01',tz='UTC'))&(q.time<pd.Timestamp('2025-01-01',tz='UTC'))].sort_values('time').drop_duplicates('time').reset_index(drop=True)
def features(x):
 x=x.copy(); pc=x.close.shift(); tr=pd.concat([x.high-x.low,(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)
 x['tr_pips']=tr/PIP; x['body_pips']=(x.close-x.open).abs()/PIP; x['median_tr96']=x.tr_pips.rolling(96).median(); x['direction']=np.sign(x.close-x.open)
 pos=(x.close-x.low)/(x.high-x.low).replace(0,np.nan); x['shock_ratio']=x.tr_pips/x.median_tr96
 x['shock']=(x.tr_pips>=2.5*x.median_tr96)&(x.body_pips>=.65*x.tr_pips); x['up_shock']=x.shock&(x.direction>0)&(pos>=.8); x['down_shock']=x.shock&(x.direction<0)&(pos<=.2)
 x['fold']=[fold_of(t) for t in x.time]; return x
def reproduce_events(x):
 mid=(x.high.shift()+x.low.shift())/2
 rows=[]
 for i in x.index[(x.up_shock.shift().fillna(False))&(x.close<mid)&(x.close<x.open)]:rows.append((int(i),-1,'up_shock_failed'))
 for i in x.index[(x.down_shock.shift().fillna(False))&(x.close>mid)&(x.close>x.open)]:rows.append((int(i),1,'down_shock_failed'))
 rows.sort(); keep=[]; active=-1
 for i,side,reason in rows:
  e=i+1; q=e+8
  if i<100 or q>=len(x) or x.fold.iloc[i]!=x.fold.iloc[q] or i<=active:continue
  keep.append({'failure_i':i,'shock_i':i-1,'entry_i':e,'exit_i':q,'side':side,'reason':reason}); active=i+9
 out=[]
 for r in keep:
  i=r['failure_i']; e=r['entry_i']; q=r['exit_i']; fold=x.fold.iloc[i]
  out.append({**r,'opportunity_id':f"{fold}|D_SHOCK_FAILURE|{x.time.iloc[e].isoformat()}|{r['side']}",'fold':fold,'signal_utc':x.time.iloc[i],'entry_utc':x.time.iloc[e],'exit_utc':x.time.iloc[q],'entry_bid':x.open.iloc[e],'exit_bid':x.open.iloc[q]})
 return pd.DataFrame(out)

class TickStore:
 def __init__(self,roots):
  self.month={}; self.tars={}; self.cache={}
  for root in roots:
   for p in Path(root).glob('*.tar.gz'):
    stem=p.name
    y=int(stem.split('-')[1]); m=int(stem.split('-')[2]); self.month[(y,m)]=p
 def tf(self,y,m):
  k=(y,m)
  if k not in self.tars:self.tars[k]=tarfile.open(self.month[k],'r:gz')
  return self.tars[k]
 def hour(self,t):
  h=pd.Timestamp(t).tz_convert('UTC').floor('h'); key=h.isoformat()
  if key in self.cache:return self.cache[key]
  name=f"{h:%Y-%m-%d}/decoded_csv/USDJPY/{h:%Y/%m/%d/%H}.csv.gz"
  try:
   raw=self.tf(h.year,h.month).extractfile(name).read(); d=pd.read_csv(io.BytesIO(gzip.decompress(raw)))
   d['timestamp_utc']=pd.to_datetime(d.timestamp_utc,utc=True); d=d[['timestamp_utc','bid','ask']].sort_values('timestamp_utc').drop_duplicates('timestamp_utc').reset_index(drop=True)
  except (KeyError,FileNotFoundError,AttributeError): d=pd.DataFrame(columns=['timestamp_utc','bid','ask'])
  self.cache[key]=d; return d
 def between(self,start,end,include_end=False):
  start=pd.Timestamp(start).tz_convert('UTC'); end=pd.Timestamp(end).tz_convert('UTC'); frames=[]
  for h in pd.date_range(start.floor('h'),end.floor('h'),freq='h'):
   q=self.hour(h)
   if len(q):frames.append(q)
  if not frames:return pd.DataFrame(columns=['timestamp_utc','bid','ask'])
  z=pd.concat(frames,ignore_index=True).sort_values('timestamp_utc').drop_duplicates('timestamp_utc')
  return z[(z.timestamp_utc>=start)&(z.timestamp_utc<=end if include_end else z.timestamp_utc<end)].reset_index(drop=True)
 def first_at_or_after(self,t,max_wait='8h',skip=0):
  t=pd.Timestamp(t).tz_convert('UTC'); z=self.between(t,t+pd.Timedelta(max_wait),include_end=True)
  return None if len(z)<=skip else z.iloc[skip]
 def bar(self,start,end):
  z=self.between(start,end)
  if z.empty:return None
  return {'open':float(z.bid.iloc[0]),'high':float(z.bid.max()),'low':float(z.bid.min()),'close':float(z.bid.iloc[-1]),'first_tick':z.timestamp_utc.iloc[0],'last_tick':z.timestamp_utc.iloc[-1],'ticks':len(z)}

def raw_features_for_event(store,x,shock_i):
 idx=range(max(0,shock_i-96),shock_i+2); bars=[]
 for j in idx:
  st=x.time.iloc[j]; en=st+pd.Timedelta('15m'); b=store.bar(st,en)
  if b is None:return None
  bars.append({'j':j,**b})
 d=pd.DataFrame(bars); pc=d.close.shift(); d['tr']=pd.concat([d.high-d.low,(d.high-pc).abs(),(d.low-pc).abs()],axis=1).max(axis=1)/PIP; d['med']=d.tr.rolling(96).median(); d['body']=(d.close-d.open).abs()/PIP
 s=d[d.j==shock_i].iloc[0]; f=d[d.j==shock_i+1].iloc[0]; pos=(s.close-s.low)/(s.high-s.low) if s.high>s.low else np.nan
 up=bool(s.tr>=2.5*s.med and s.body>=.65*s.tr and s.close>s.open and pos>=.8); dn=bool(s.tr>=2.5*s.med and s.body>=.65*s.tr and s.close<s.open and pos<=.2); midpoint=(s.high+s.low)/2
 fail_short=bool(f.close<midpoint and f.close<f.open); fail_long=bool(f.close>midpoint and f.close>f.open)
 return {'shock_open':s.open,'shock_high':s.high,'shock_low':s.low,'shock_close':s.close,'shock_tr_pips':s.tr,'shock_median_tr96':s.med,'shock_ratio':s.tr/s.med if s.med else np.nan,'raw_up_shock':up,'raw_down_shock':dn,'raw_shock_direction':('UP' if s.close>s.open else ('DOWN' if s.close<s.open else 'FLAT')),'failure_open':f.open,'failure_high':f.high,'failure_low':f.low,'failure_close':f.close,'failure_short':fail_short,'failure_long':fail_long,'midpoint':midpoint,'shock_ticks':int(s.ticks),'failure_ticks':int(f.ticks)}

def executable_trade(store,event,candidate,entry_delay='BASELINE'):
 boundary=pd.Timestamp(event.entry_utc); side=int(event.side)
 if candidate=='C_M1_ACCEPTANCE_8BAR':
  mstart=boundary.ceil('min'); mend=mstart+pd.Timedelta('1m'); z=store.between(mstart,mend)
  if z.empty:return None
  op=float(z.bid.iloc[0]); cl=float(z.bid.iloc[-1]); midpoint=float(event.shock_midpoint)
  ok=(side>0 and cl>midpoint and cl>op) or (side<0 and cl<midpoint and cl<op)
  if not ok:return {'admitted':False,'confirmation_open':op,'confirmation_close':cl,'confirmation_end':mend}
  boundary=mend
 if entry_delay=='ONE_TICK': ent=store.first_at_or_after(boundary,skip=1)
 elif entry_delay in ('FIVE_SECONDS','FIFTEEN_SECONDS'):
  ent=store.first_at_or_after(boundary+pd.Timedelta(seconds=5 if entry_delay=='FIVE_SECONDS' else 15))
 else: ent=store.first_at_or_after(boundary)
 if ent is None:return None
 exit_boundary=pd.Timestamp(event.exit4_utc if candidate=='D_EXECUTABLE_T0_4BAR' else event.exit_utc)
 ex=store.first_at_or_after(exit_boundary)
 if ex is None:return None
 entry_bid=float(ent.bid); entry_ask=float(ent.ask); exit_bid=float(ex.bid); exit_ask=float(ex.ask)
 pips=(exit_bid-entry_ask)/PIP if side>0 else (entry_bid-exit_ask)/PIP
 path=store.between(ent.timestamp_utc,ex.timestamp_utc,include_end=True)
 if path.empty:mfe=mae=np.nan
 elif side>0:
  q=(path.bid-entry_ask)/PIP; mfe=float(q.max()); mae=float(q.min())
 else:
  q=(entry_bid-path.ask)/PIP; mfe=float(q.max()); mae=float(q.min())
 return {'admitted':True,'entry_tick_utc':ent.timestamp_utc,'exit_tick_utc':ex.timestamp_utc,'entry_bid_exec':entry_bid,'entry_ask_exec':entry_ask,'exit_bid_exec':exit_bid,'exit_ask_exec':exit_ask,'observed_spread_entry_pips':(entry_ask-entry_bid)/PIP,'observed_spread_exit_pips':(exit_ask-exit_bid)/PIP,'pnl_pips':pips,'pnl_jpy':pips*JPYPP,'mfe_pips':mfe,'mae_pips':mae,'holding_seconds':(ex.timestamp_utc-ent.timestamp_utc).total_seconds()}

def baseline_context(events,b):
 b=b.copy(); b['entry_utc']=pd.to_datetime(b.entry_utc,utc=True); b['close_utc']=pd.to_datetime(b.close_utc,utc=True); b['realized_pl_jpy']=b.realized_pl_jpy.astype(float); b=b.sort_values('close_utc').reset_index(drop=True); b['trade_id']=[f"{r.fold}|{r.strategy}|{r.entry_utc.isoformat()}|{int(r.side)}" for r in b.itertuples()]
 daily=b.groupby(b.entry_utc.dt.strftime('%Y-%m-%d')).realized_pl_jpy.sum(); daymap=daily.to_dict()
 eq=0.; peak=0.; dd_at=[]
 for r in events.itertuples():
  done=b[b.close_utc<=r.entry_utc]; e=float(done.realized_pl_jpy.sum()); p=float(done.realized_pl_jpy.cumsum().cummax().max()) if len(done) else 0.; dd=max(0,p-e); dd_at.append(dd)
 events=events.copy(); events['baseline_day_pnl_jpy']=events.entry_utc.dt.strftime('%Y-%m-%d').map(daymap).fillna(0.); events['baseline_day_state']=np.select([events.baseline_day_pnl_jpy>0,events.baseline_day_pnl_jpy<0],['POSITIVE','NEGATIVE'],default='FLAT'); events['baseline_existing_drawdown_jpy']=dd_at
 clusters=[]; losses=b[b.realized_pl_jpy<0].sort_values('close_utc')
 cur=[]
 for r in losses.itertuples():
  if not cur or r.close_utc-cur[-1].close_utc<=pd.Timedelta('60m'):cur.append(r)
  else:
   if len(cur)>=2:clusters.append((cur[0].close_utc,cur[-1].close_utc,len(cur)))
   cur=[r]
 if len(cur)>=2:clusters.append((cur[0].close_utc,cur[-1].close_utc,len(cur)))
 rows=[]
 for r in events.itertuples():
  active=b[(b.entry_utc<r.exit_utc)&(b.close_utc>r.entry_utc)]; same=active[active.side==r.side]; opp=active[active.side!=r.side]
  near=any(r.entry_utc>=a-pd.Timedelta('60m') and r.entry_utc<=z+pd.Timedelta('60m') for a,z,n in clusters)
  rows.append({'opportunity_id':r.opportunity_id,'b02_active':bool((active.strategy=='B02').any()),'f05_active':bool((active.strategy=='F05').any()),'both_active':bool((active.strategy=='B02').any() and (active.strategy=='F05').any()),'neither_active':len(active)==0,'active_count':len(active),'same_direction_overlap':len(same)>0,'opposite_direction_overlap':len(opp)>0,'active_trade_ids':';'.join(active.trade_id),'loss_cluster_nearby':near})
 return events.merge(pd.DataFrame(rows),on='opportunity_id',how='left'),b,clusters

def metric_row(g,candidate,scenario='BASELINE'):
 g=g[g.get('admitted',True).fillna(False)] if 'admitted' in g else g
 s=g.pnl_jpy.astype(float) if len(g) else pd.Series(dtype=float); mdd,rec=maxdd_from_timed(g) if len(g) else (0.,0.)
 months=g.assign(month=g.exit_utc.dt.strftime('%Y-%m')).groupby('month').pnl_jpy.sum() if len(g) else pd.Series(dtype=float)
 dates=g.assign(date=g.exit_utc.dt.strftime('%Y-%m-%d')).groupby('date').pnl_jpy.sum() if len(g) else pd.Series(dtype=float)
 gross=float(s[s>0].sum()); loss=float(s[s<0].sum()); pos_events=s[s>0].sort_values(ascending=False)
 return {'candidate_id':candidate,'scenario':scenario,'event_count':int(g.opportunity_id.nunique()) if len(g) else 0,'trades':len(g),'gross_profit_jpy':gross,'gross_loss_jpy':loss,'net_profit_jpy':float(s.sum()),'profit_factor':pf(s),'win_rate':float((s>0).mean()) if len(s) else None,'average_pnl_jpy':float(s.mean()) if len(s) else None,'median_pnl_jpy':float(s.median()) if len(s) else None,'maximum_win_jpy':float(s.max()) if len(s) else None,'maximum_loss_jpy':float(s.min()) if len(s) else None,'average_mfe_pips':float(g.mfe_pips.mean()) if len(g) and 'mfe_pips' in g else None,'average_mae_pips':float(g.mae_pips.mean()) if len(g) and 'mae_pips' in g else None,'median_holding_minutes':float(g.holding_seconds.median()/60) if len(g) and 'holding_seconds' in g else 120.,'maximum_drawdown_jpy':mdd,'recovery_hours':rec,'active_months':len(months),'positive_months':int((months>0).sum()),'month_breadth':float((months>0).mean()) if len(months) else 0.,'positive_folds':int((g.groupby('fold').pnl_jpy.sum().reindex(FOLDS,fill_value=0)>0).sum()) if len(g) else 0,'positive_side_fold_cells':int((g.groupby(['fold','side_label']).pnl_jpy.sum()>0).sum()) if len(g) else 0,'positive_session_cells':int((g.groupby('session').pnl_jpy.sum()>0).sum()) if len(g) else 0,'top_date_concentration':float(dates.max()/gross) if gross>0 and len(dates) else None,'top_event_concentration':float(pos_events.iloc[0]/gross) if gross>0 and len(pos_events) else None}

def slice_metrics(df,by,outpath):
 rows=[]
 for (cand,*keys),g in df.groupby(['candidate_id']+by,dropna=False):
  r=metric_row(g,cand); r.update({k:v for k,v in zip(by,keys)}); rows.append(r)
 pd.DataFrame(rows).to_csv(outpath,index=False)

def daily_corr(g,b):
 idx=pd.Index(pd.date_range('2023-01-01','2024-12-31',tz='UTC').strftime('%Y-%m-%d'))
 cand=g.assign(date=g.exit_utc.dt.strftime('%Y-%m-%d')).groupby('date').pnl_jpy.sum().reindex(idx,fill_value=0.)
 rows={}
 for st in ['B02','F05']:
  q=b[b.strategy==st].assign(date=lambda x:x.close_utc.dt.strftime('%Y-%m-%d')).groupby('date').realized_pl_jpy.sum().reindex(idx,fill_value=0.)
  rows[st]=0. if cand.std()==0 or q.std()==0 else float(cand.corr(q))
 return rows,cand

def concentration(g):
 rows=[]
 def add(name,z):
  r=metric_row(z,g.candidate_id.iloc[0],name); rows.append(r)
 add('BASELINE',g)
 s=g.sort_values('pnl_jpy',ascending=False)
 for n in [1,3,5]:add(f'REMOVE_TOP_{n}_EVENTS',s.iloc[n:])
 day=g.assign(key=g.exit_utc.dt.strftime('%Y-%m-%d')).groupby('key').pnl_jpy.sum(); best=day.idxmax();add('REMOVE_BEST_DAY',g[g.exit_utc.dt.strftime('%Y-%m-%d')!=best])
 mon=g.assign(key=g.exit_utc.dt.strftime('%Y-%m')).groupby('key').pnl_jpy.sum(); bestm=mon.idxmax();add('REMOVE_BEST_MONTH',g[g.exit_utc.dt.strftime('%Y-%m')!=bestm])
 wins=s[s.pnl_jpy>0]; n=max(1,math.ceil(len(wins)*.1)); ids=set(wins.head(n).opportunity_id);add('REMOVE_TOP_DECILE_WINS',g[~g.opportunity_id.isin(ids)])
 for q in sorted(g.session.unique()):add(f'REMOVE_SESSION_{q}',g[g.session!=q])
 for q in ['LONG','SHORT']:add(f'REMOVE_SIDE_{q}',g[g.side_label!=q])
 for q in FOLDS:add(f'REMOVE_FOLD_{q}',g[g.fold!=q])
 return rows

def stress(g):
 rows=[]
 scenarios=[('OBSERVED',0,0,'BASELINE'),('SPREAD_PLUS_0_5',.5,0,'BASELINE'),('SPREAD_PLUS_1_0',1,0,'BASELINE'),('SLIPPAGE_0_5',0,.5,'BASELINE'),('SLIPPAGE_1_0',0,1,'BASELINE'),('SEVERE',1,1,'FIFTEEN_SECONDS')]
 for name,sp,sl,delay in scenarios:
  z=g.copy()
  if delay!='BASELINE' and f'pnl_jpy_{delay}' in z:z['pnl_jpy']=z[f'pnl_jpy_{delay}']; z=z[z.pnl_jpy.notna()].copy()
  z['pnl_jpy']=z.pnl_jpy-(sp+2*sl)*JPYPP
  r=metric_row(z,g.candidate_id.iloc[0],name); r.update(extra_spread_pips=sp,slippage_pips_per_execution=sl,entry_delay=delay);rows.append(r)
 return rows

def lofo(df):
 rows=[]
 for held in FOLDS:
  train=df[df.fold!=held]; scores=[]
  for cand in ELIGIBLE:
   g=train[(train.candidate_id==cand)&train.admitted.fillna(False)].copy()
   if g.empty:continue
   folds=g.groupby('fold').pnl_jpy.sum(); c=concentration(g); cm={r['scenario']:r for r in c}; gate=g.pnl_jpy.sum()>0 and int((folds>0).sum())>=2 and cm['REMOVE_BEST_DAY']['net_profit_jpy']>0 and cm['REMOVE_TOP_3_EVENTS']['net_profit_jpy']>0
   stressp=g.pnl_jpy-(.5+1.0)*JPYPP
   med=float(pd.DataFrame({'fold':g.fold,'v':stressp}).groupby('fold').v.sum().median())
   scores.append({'candidate_id':cand,'gate':gate,'median_train_cost_net':med,'train_pf':pf(g.pnl_jpy),'median_hold':g.holding_seconds.median()})
  ok=[x for x in scores if x['gate']]; pool=ok if ok else scores
  sel=sorted(pool,key=lambda x:(-x['median_train_cost_net'],-(x['train_pf'] or -1),x['median_hold'],x['candidate_id']))[0]
  h=df[(df.fold==held)&(df.candidate_id==sel['candidate_id'])&df.admitted.fillna(False)].copy(); severe=h.copy(); severe['pnl_jpy']=severe.get('pnl_jpy_FIFTEEN_SECONDS',severe.pnl_jpy)-(1+2)*JPYPP
  hc={r['scenario']:r for r in concentration(h)} if len(h) else {}
  rows.append({'held_out_fold':held,'selected_candidate':sel['candidate_id'],'training_gate_passed':sel['gate'],'training_candidates':json.dumps(clean(scores),sort_keys=True),'held_out_trades':len(h),'held_out_net_jpy':float(h.pnl_jpy.sum()),'held_out_pf':pf(h.pnl_jpy),'held_out_severe_net_jpy':float(severe.pnl_jpy.sum()),'held_out_severe_pf':pf(severe.pnl_jpy),'held_out_best_day_excluded_net_jpy':hc.get('REMOVE_BEST_DAY',{}).get('net_profit_jpy'),'held_out_top3_excluded_net_jpy':hc.get('REMOVE_TOP_3_EVENTS',{}).get('net_profit_jpy')})
 return pd.DataFrame(rows)

def bootstrap(g,seed=20260726,n=10000):
 rng=np.random.default_rng(seed); vals=g.pnl_jpy.to_numpy(); ev=np.array([rng.choice(vals,len(vals),replace=True).sum() for _ in range(n)]) if len(vals) else np.array([0])
 days=[x.pnl_jpy.to_numpy() for _,x in g.assign(date=g.exit_utc.dt.strftime('%Y-%m-%d')).groupby('date')]
 dsum=np.array([x.sum() for x in days]); dayb=np.array([rng.choice(dsum,len(dsum),replace=True).sum() for _ in range(n)]) if len(dsum) else np.array([0])
 return {'event_bootstrap_net_ci95_jpy':[float(np.quantile(ev,.025)),float(np.quantile(ev,.975))],'event_bootstrap_probability_positive':float((ev>0).mean()),'day_block_bootstrap_net_ci95_jpy':[float(np.quantile(dayb,.025)),float(np.quantile(dayb,.975))],'day_block_probability_positive':float((dayb>0).mean()),'replicates':n}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--m15-2023',type=Path,required=True);ap.add_argument('--m15-2024',type=Path,required=True);ap.add_argument('--csos-ledger',type=Path,required=True);ap.add_argument('--baseline-trades',type=Path,required=True);ap.add_argument('--raw-2023',type=Path,required=True);ap.add_argument('--raw-2024',type=Path,required=True);ap.add_argument('--prereg',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);ap.add_argument('--research-sha',default='UNKNOWN');ap.add_argument('--core-sha',default='UNKNOWN');ap.add_argument('--run-id',default='LOCAL');a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 pre=json.load(open(a.prereg)); assert pre['development_folds']==FOLDS and set(pre['forbidden_periods'])=={'2025H1','2025H2'} and pre['boundaries']['2025_price_or_outcome_access'] is False
 b23=load_bars23(a.m15_2023);b24=load_bars24(a.m15_2024);x=features(pd.concat([b23,b24],ignore_index=True).sort_values('time').reset_index(drop=True));assert x.time.dt.year.max()==2024
 rep=reproduce_events(x); cs=pd.read_csv(a.csos_ledger);cs=cs[cs.variant=='D_SHOCK_FAILURE'].copy();cs['entry_utc']=pd.to_datetime(cs.entry_utc,utc=True);cs['exit_utc']=pd.to_datetime(cs.exit_utc,utc=True);cs['signal_utc']=pd.to_datetime(cs.signal_utc,utc=True);cs=cs.sort_values('opportunity_id').reset_index(drop=True);rep=rep.sort_values('opportunity_id').reset_index(drop=True)
 missing=sorted(set(cs.opportunity_id)-set(rep.opportunity_id));extra=sorted(set(rep.opportunity_id)-set(cs.opportunity_id)); assert len(cs)==114 and not missing and not extra
 e=rep.merge(cs[['opportunity_id','normalized_pl_jpy','net_pips','near_entry_B02','near_entry_F05','simultaneous_B02','simultaneous_F05','simultaneous_any_baseline']],on='opportunity_id',validate='one_to_one')
 e['shock_start_utc']=[x.time.iloc[int(i)] for i in e.shock_i]; e['shock_end_utc']=[x.time.iloc[int(i)] for i in e.failure_i]; e['failure_start_utc']=e.signal_utc; e['failure_end_utc']=e.entry_utc; e['shock_direction']=np.where(e.side==-1,'UP','DOWN');e['side_label']=np.where(e.side>0,'LONG','SHORT');e['session']=[session_of(t) for t in e.entry_utc];e['shock_midpoint']=(x.high.iloc[e.shock_i].to_numpy()+x.low.iloc[e.shock_i].to_numpy())/2;e['shock_ratio']=x.shock_ratio.iloc[e.shock_i].to_numpy();e['shock_tr_pips']=x.tr_pips.iloc[e.shock_i].to_numpy();e['shock_body_pips']=x.body_pips.iloc[e.shock_i].to_numpy()
 runs=[]
 for j in e.shock_i:
  d=int(x.direction.iloc[j]);n=0;k=j
  while k>=0 and int(x.direction.iloc[k])==d:n+=1;k-=1
  runs.append(n)
 e['impulse_run_bars']=runs;e['shock_size_bucket']=pd.cut(e.shock_ratio,[2.5,3,4,np.inf],right=False,labels=['2.50_to_lt_3.00','3.00_to_lt_4.00','ge_4.00']).astype(str);e['shock_duration_bucket']=np.select([e.impulse_run_bars==1,e.impulse_run_bars==2],['1_BAR','2_BARS'],default='GE_3_BARS')
 e['exit4_utc']=[x.time.iloc[int(i)+4] for i in e.entry_i]
 baseline=pd.read_csv(a.baseline_trades); e,baseline,clusters=baseline_context(e,baseline)
 store=TickStore([a.raw_2023,a.raw_2024]); chron=[]; trades=[]
 for ev in e.itertuples(index=False):
  rf=raw_features_for_event(store,x,int(ev.shock_i)); source='DUKASCOPY_RAW_MATCHED' if pd.Timestamp(ev.entry_utc).year==2024 else 'DUKASCOPY_RAW_VS_RAKUTEN_ACCEPTED_BAR'
  if rf is None: status='UNRESOLVED'; contradiction=True;rf={}
  else:
   if pd.Timestamp(ev.entry_utc).year==2024:
    expected_ok=(ev.side<0 and rf['raw_up_shock'] and rf['failure_short']) or (ev.side>0 and rf['raw_down_shock'] and rf['failure_long'])
    status='EXACT_CONFIRMED' if expected_ok else 'UNRESOLVED'; contradiction=not expected_ok
   else:
    direction_ok=(ev.side<0 and rf['raw_shock_direction']=='UP' and rf['failure_short']) or (ev.side>0 and rf['raw_shock_direction']=='DOWN' and rf['failure_long'])
    status='BOUNDED_SOURCE_MISMATCH' if direction_ok else 'UNRESOLVED'; contradiction=not direction_ok
  cross=None
  if rf:
   fz=store.between(ev.failure_start_utc,ev.failure_end_utc)
   if len(fz):
    q=fz[fz.bid<ev.shock_midpoint] if ev.side<0 else fz[fz.bid>ev.shock_midpoint];cross=q.timestamp_utc.iloc[0] if len(q) else None
  ent=store.first_at_or_after(ev.entry_utc); leakage=bool(ent is not None and ent.timestamp_utc<ev.failure_end_utc)
  chron.append({'opportunity_id':ev.opportunity_id,'source_relation':source,'chronology_status':status,'material_predicate_contradiction':contradiction,'midpoint_first_cross_utc':cross,'first_executable_tick_utc':None if ent is None else ent.timestamp_utc,'entry_before_failure_close':leakage,**rf})
  base={'opportunity_id':ev.opportunity_id,'candidate_id':'A_CSOS_FIXED_BAR','fold':ev.fold,'side':ev.side,'side_label':ev.side_label,'session':ev.session,'entry_utc':ev.entry_utc,'exit_utc':ev.exit_utc,'admitted':True,'pnl_pips':ev.net_pips,'pnl_jpy':ev.normalized_pl_jpy,'mfe_pips':np.nan,'mae_pips':np.nan,'holding_seconds':(ev.exit_utc-ev.entry_utc).total_seconds()}; trades.append(base)
  for cand in ELIGIBLE:
   r=executable_trade(store,ev,cand)
   if r is None:r={'admitted':False}
   row={'opportunity_id':ev.opportunity_id,'candidate_id':cand,'fold':ev.fold,'side':ev.side,'side_label':ev.side_label,'session':ev.session,'entry_utc':ev.entry_utc,'exit_utc':ev.exit4_utc if cand=='D_EXECUTABLE_T0_4BAR' else ev.exit_utc,**r}
   for delay in ['ONE_TICK','FIVE_SECONDS','FIFTEEN_SECONDS']:
    rd=executable_trade(store,ev,cand,delay)
    row[f'pnl_jpy_{delay}']=np.nan if rd is None or not rd.get('admitted',False) else rd['pnl_jpy']
   trades.append(row)
 chron=pd.DataFrame(chron);tr=pd.DataFrame(trades); tr=tr.merge(e.drop(columns=['side','side_label','session','fold','entry_utc','exit_utc'],errors='ignore'),on='opportunity_id',how='left');tr['admitted']=tr.admitted.fillna(False)
 # Duplicate and identity audit
 identity={'expected_csos_events':114,'reproduced_events':len(rep),'missing_event_ids':missing,'extra_event_ids':extra,'duplicate_event_ids':int(e.opportunity_id.duplicated().sum()),'duplicate_shock_start_times':int(e.shock_start_utc.duplicated().sum()),'overlapping_duplicate_intervals':int(sum(e.entry_utc.iloc[i]<e.exit_utc.iloc[i-1] for i in range(1,len(e)))),'same_shock_double_count':int(e.groupby('shock_start_utc').size().gt(1).sum()),'timezone_mismatch_count':int((e.entry_utc.dt.tz is None) if hasattr(e.entry_utc.dt,'tz') else 0),'bar_close_leakage_count':int(chron.entry_before_failure_close.sum())}
 write_json(a.out_dir/'event_identity_audit.json',identity);e.to_csv(a.out_dir/'event_identity_ledger.csv',index=False);chron.to_csv(a.out_dir/'chronology_audit.csv',index=False);tr.to_csv(a.out_dir/'candidate_trade_ledger.csv.gz',index=False,compression='gzip')
 # Metrics and slices
 metrics=[]
 for cand,g in tr.groupby('candidate_id'):metrics.append(metric_row(g[g.admitted],cand))
 metrics=pd.DataFrame(metrics);metrics.to_csv(a.out_dir/'candidate_metrics.csv',index=False)
 slice_metrics(tr[tr.admitted],['fold'],a.out_dir/'fold_metrics.csv');slice_metrics(tr[tr.admitted],['side_label'],a.out_dir/'side_metrics.csv');slice_metrics(tr[tr.admitted],['session'],a.out_dir/'session_metrics.csv');slice_metrics(tr[tr.admitted],['shock_size_bucket'],a.out_dir/'shock_size_metrics.csv');slice_metrics(tr[tr.admitted],['shock_duration_bucket'],a.out_dir/'shock_duration_metrics.csv');slice_metrics(tr[tr.admitted],['baseline_day_state'],a.out_dir/'baseline_state_metrics.csv')
 costs=[];conc=[];corrows=[];overrows=[]
 for cand in ELIGIBLE:
  g=tr[(tr.candidate_id==cand)&tr.admitted].copy(); costs+=stress(g);conc+=concentration(g);cors,day=daily_corr(g,baseline); weak=g[g.baseline_day_state=='NEGATIVE']; weakloss=-baseline.assign(date=baseline.close_utc.dt.strftime('%Y-%m-%d')).groupby('date').realized_pl_jpy.sum().clip(upper=0).sum();corrows.append({'candidate_id':cand,'correlation_to_B02':cors['B02'],'correlation_to_F05':cors['F05'],'weak_market_net_jpy':float(weak.pnl_jpy.sum()),'weak_market_coverage':float(weak.pnl_jpy.clip(lower=0).sum()/weakloss) if weakloss else 0.,'overlap_rate':float((g.active_count>0).mean()),'same_direction_overlap_rate':float(g.same_direction_overlap.mean()),'opposite_direction_overlap_rate':float(g.opposite_direction_overlap.mean()),'existing_drawdown_rate':float((g.baseline_existing_drawdown_jpy>0).mean()),'loss_cluster_nearby_rate':float(g.loss_cluster_nearby.mean())})
  overrows.extend(g.groupby(['b02_active','f05_active','same_direction_overlap','opposite_direction_overlap'],dropna=False).agg(trades=('pnl_jpy','size'),net_jpy=('pnl_jpy','sum'),mean_jpy=('pnl_jpy','mean')).reset_index().assign(candidate_id=cand).to_dict('records'))
 pd.DataFrame(costs).to_csv(a.out_dir/'cost_stress_report.csv',index=False);pd.DataFrame(conc).to_csv(a.out_dir/'concentration_report.csv',index=False);pd.DataFrame(corrows).to_csv(a.out_dir/'complementarity_metrics.csv',index=False);pd.DataFrame(overrows).to_csv(a.out_dir/'overlap_report.csv',index=False)
 delays=[]
 for cand in ELIGIBLE:
  g=tr[(tr.candidate_id==cand)&tr.admitted]
  for delay in ['ONE_TICK','FIVE_SECONDS','FIFTEEN_SECONDS']:
   z=g[g[f'pnl_jpy_{delay}'].notna()].copy();z['pnl_jpy']=z[f'pnl_jpy_{delay}'];r=metric_row(z,cand,delay);delays.append(r)
 pd.DataFrame(delays).to_csv(a.out_dir/'execution_delay_report.csv',index=False)
 # Portfolio interactions using B as primary preselection reference
 portfolio=[]; eqcurves=[]
 base_events=baseline[['trade_id','close_utc','realized_pl_jpy']].rename(columns={'close_utc':'exit_utc','realized_pl_jpy':'pnl_jpy'}).assign(component='BASELINE')
 base_mdd,_=maxdd_from_timed(base_events)
 for cand in ELIGIBLE:
  g=tr[(tr.candidate_id==cand)&tr.admitted].copy(); modes={'STANDALONE':g,'ADDITIVE':g,'SKIP_SAME_DIRECTION':g[~g.same_direction_overlap],'SKIP_OPPOSITE_DIRECTION':g[~g.opposite_direction_overlap],'MAX_CONCURRENT_2':g[g.active_count<2],'SKIP_BASELINE_DRAWDOWN':g[g.baseline_existing_drawdown_jpy<=0]}
  for mode,z in modes.items():
   ce=z[['opportunity_id','exit_utc','pnl_jpy']].rename(columns={'opportunity_id':'trade_id'}).assign(component='SHOCK_FAILURE')
   allx=ce if mode=='STANDALONE' else pd.concat([base_events,ce],ignore_index=True)
   mdd,_=maxdd_from_timed(allx); net=float(allx.pnl_jpy.sum());peak=int(z.active_count.max()+1) if len(z) else 0; margin=float((z.entry_bid*1000/25).max()) if len(z) else 0.
   portfolio.append({'candidate_id':cand,'mode':mode,'candidate_trades':len(z),'portfolio_net_jpy':net,'portfolio_mdd_jpy':mdd,'baseline_mdd_jpy':base_mdd,'mdd_change_fraction':(mdd-base_mdd)/base_mdd if base_mdd else None,'peak_concurrent_positions_estimate':peak,'incremental_margin_jpy_estimate_at_25x':margin})
   if cand=='B_EXECUTABLE_T0_8BAR' and mode in ('STANDALONE','ADDITIVE'):
    q=allx.sort_values('exit_utc');q['equity_jpy']=q.pnl_jpy.cumsum();q['candidate_id']=cand;q['mode']=mode;eqcurves.append(q[['exit_utc','candidate_id','mode','component','pnl_jpy','equity_jpy']])
  # replacement: deterministic shock-priority removes all active baseline trades at trigger
  remove=set(';'.join(g.active_trade_ids.fillna('')).split(';'));remove.discard('');rb=base_events[~base_events.trade_id.isin(remove)];ce=g[['opportunity_id','exit_utc','pnl_jpy']].rename(columns={'opportunity_id':'trade_id'}).assign(component='SHOCK_FAILURE');allx=pd.concat([rb,ce]);mdd,_=maxdd_from_timed(allx);portfolio.append({'candidate_id':cand,'mode':'REPLACEMENT_SHOCK_PRIORITY','candidate_trades':len(g),'portfolio_net_jpy':float(allx.pnl_jpy.sum()),'portfolio_mdd_jpy':mdd,'baseline_mdd_jpy':base_mdd,'mdd_change_fraction':(mdd-base_mdd)/base_mdd if base_mdd else None,'peak_concurrent_positions_estimate':None,'incremental_margin_jpy_estimate_at_25x':None})
  # oracle replacement separately
  oracle=0.
  for r in g.itertuples():
   ids=[x for x in str(r.active_trade_ids).split(';') if x];bp=baseline[baseline.trade_id.isin(ids)].realized_pl_jpy.sum();oracle+=max(float(r.pnl_jpy),float(bp))
  portfolio.append({'candidate_id':cand,'mode':'ORACLE_CONFLICT_WINNER_NONIMPLEMENTABLE','candidate_trades':len(g),'portfolio_net_jpy':float(baseline.realized_pl_jpy.sum()+oracle),'portfolio_mdd_jpy':None,'baseline_mdd_jpy':base_mdd,'mdd_change_fraction':None,'peak_concurrent_positions_estimate':None,'incremental_margin_jpy_estimate_at_25x':None})
 pd.DataFrame(portfolio).to_csv(a.out_dir/'portfolio_interaction_report.csv',index=False);pd.concat(eqcurves).to_csv(a.out_dir/'equity_curves.csv',index=False)
 # LOFO and ranking
 l=lofo(tr[tr.candidate_id.isin(ELIGIBLE)]);l.to_csv(a.out_dir/'lofo_selection_results.csv',index=False)
 ranking=[]
 for cand in ELIGIBLE:
  g=tr[(tr.candidate_id==cand)&tr.admitted];c={r['scenario']:r for r in concentration(g)};co={r['scenario']:r for r in stress(g)};m=metric_row(g,cand);lo=l[l.selected_candidate==cand];rank={'candidate_id':cand,**m,'lofo_selected_count':len(lo),'lofo_positive_heldout_count':int((lo.held_out_net_jpy>0).sum()),'best_day_excluded_net_jpy':c['REMOVE_BEST_DAY']['net_profit_jpy'],'top3_excluded_net_jpy':c['REMOVE_TOP_3_EVENTS']['net_profit_jpy'],'spread_plus_1_net_jpy':co['SPREAD_PLUS_1_0']['net_profit_jpy'],'severe_net_jpy':co['SEVERE']['net_profit_jpy'],'severe_pf':co['SEVERE']['profit_factor']};ranking.append(rank)
 ranking=pd.DataFrame(ranking)
 ranking['all_fold_training_gate']=(ranking.net_profit_jpy>0)&(ranking.positive_folds>=3)&(ranking.best_day_excluded_net_jpy>0)&(ranking.top3_excluded_net_jpy>0)
 ranking['median_fold_cost_net_jpy']=[float((tr[(tr.candidate_id==c)&tr.admitted].assign(cost_net=lambda q:q.pnl_jpy-15.0).groupby('fold').cost_net.sum().reindex(FOLDS,fill_value=0)).median()) for c in ranking.candidate_id]
 pool=ranking[ranking.all_fold_training_gate] if ranking.all_fold_training_gate.any() else ranking
 selected=str(pool.sort_values(['median_fold_cost_net_jpy','profit_factor','median_holding_minutes','candidate_id'],ascending=[False,False,True,True]).iloc[0].candidate_id)
 ranking['selected_all_fold']=ranking.candidate_id.eq(selected);ranking=ranking.sort_values(['selected_all_fold','lofo_positive_heldout_count','median_fold_cost_net_jpy'],ascending=False);ranking.to_csv(a.out_dir/'candidate_ranking.csv',index=False)
 sg=tr[(tr.candidate_id==selected)&tr.admitted];sm=ranking[ranking.candidate_id==selected].iloc[0];comp=pd.DataFrame(corrows).set_index('candidate_id').loc[selected];padd=pd.DataFrame(portfolio);padd=padd[(padd.candidate_id==selected)&(padd['mode']=='ADDITIVE')].iloc[0]
 side=sg.groupby('side_label').pnl_jpy.sum();sidefold=sg.groupby(['side_label','fold']).pnl_jpy.sum();unresolved=float((chron.chronology_status=='UNRESOLVED').mean());contr=float(chron.material_predicate_contradiction.mean());heldpos=int((l.held_out_net_jpy>0).sum());gate_checks={'held_out_positive_3_of_4':heldpos>=3,'observed_net_positive':sm.net_profit_jpy>0,'observed_pf_ge_1_20':(sm.profit_factor or 0)>=1.2,'spread_plus_1_net_positive':sm.spread_plus_1_net_jpy>0,'severe_net_nonnegative':sm.severe_net_jpy>=0,'severe_pf_ge_1':(sm.severe_pf or 0)>=1,'best_day_excluded_positive':sm.best_day_excluded_net_jpy>0,'top3_excluded_positive':sm.top3_excluded_net_jpy>0,'both_sides_positive':all(side.reindex(['LONG','SHORT'],fill_value=0)>0),'each_side_positive_fold_cell':all(sidefold.groupby(level=0).apply(lambda q:(q>0).sum()).reindex(['LONG','SHORT'],fill_value=0)>=1),'weak_market_net_positive':comp.weak_market_net_jpy>0,'chronology_unresolved_within_limit':unresolved<=.05,'chronology_contradiction_within_limit':contr<=.05,'combined_mdd_increase_within_10pct':padd.mdd_change_fraction<=.10}
 if unresolved>.05 or contr>.05:decision='DATA_AUTHORITY_BLOCKED'
 elif all(gate_checks.values()):decision='PASS_PORTABLE_RESEARCH_CANDIDATE'
 elif sm.net_profit_jpy>0 and (sm.profit_factor or 0)>1:decision='PROMISING_NONPORTABLE_MECHANISM'
 else:decision='REJECT_SHOCK_FAILURE_FAMILY'
 stats=bootstrap(sg);write_json(a.out_dir/'statistical_robustness.json',{'selected_candidate':selected,**stats})
 final={'schema_version':'usdjpy_csos_shock_failure_phase2_final_v1','status':decision,'selected_candidate':selected,'candidate_freeze_allowed':decision=='PASS_PORTABLE_RESEARCH_CANDIDATE','proceed_to_2025_gate':False,'core_or_mt4_authorized':False,'gate_checks':gate_checks,'chronology':{'unresolved_rate':unresolved,'material_contradiction_rate':contr,'status_counts':chron.chronology_status.value_counts().to_dict()},'csos_event_reproduction':identity,'selected_metrics':sm.to_dict(),'complementarity':comp.to_dict(),'portfolio_additive':padd.to_dict(),'statistical_robustness':stats,'boundaries':{'2025_accessed':False,'B02_F05_changed':False,'Core_changed':False,'MT4_accessed':False,'production_authorized':False}}
 write_json(a.out_dir/'final_decision.json',final)
 # Source inventory, mechanism and reports
 m23=next(iter(a.raw_2023.glob('*annual-manifest.json')),None);m24=next(iter(a.raw_2024.glob('*annual-manifest.json')),None)
 src={'2023_raw_ticks':{'release':'usdjpy-2023-raw-bidask-ticks-v1','source':'Dukascopy BI5 public Bid/Ask','period':'2023','timeframe':'tick','timezone':'UTC','bid_ask':True,'raw_tick':True,'annual_manifest_sha256':sha256_file(m23) if m23 else None,'limitation':'not Rakuten broker-native; chronology is bounded against accepted Rakuten-derived M15 identity'},'2024_raw_ticks':{'release':'usdjpy-2024-raw-bidask-ticks-v1','source':'Dukascopy BI5 public Bid/Ask','period':'2024','timeframe':'tick','timezone':'UTC','bid_ask':True,'raw_tick':True,'annual_manifest_sha256':sha256_file(m24) if m24 else None,'limitation':'not Rakuten broker-native; same source as accepted derived 2024 bars'},'2023_signal_bars':{'sha256':sha256_file(a.m15_2023),'source':'accepted Rakuten MT4-derived Bid M15','bar_construction':'historical server-time conversion with preserved first-tick identity'},'2024_signal_bars':{'sha256':sha256_file(a.m15_2024),'source':'accepted Dukascopy Bid/Ask-derived M15','bar_construction':'UTC raw Tick aggregation'},'baseline_trades':{'sha256':sha256_file(a.baseline_trades),'trades':len(baseline)}};write_json(a.out_dir/'source_authority_inventory.json',src)
 write_json(a.out_dir/'csos_evidence_audit.json',{'scientific_ref':'88b88cd01bb84fafdf2e097401222d4f9dac1c6d','evaluator_ref':'11643bd5c9d04dec1d8df34e681b6516cc39264b','pr':295,'pr_head':'74c9dc6869c805e3ec3fe1db87e5744ef62729b6','release':'usdjpy-csos-opportunity-atlas-v1-r1','run_id':30202535070,'artifact_id':8632092013,'artifact_digest':'sha256:c56754eafad6e52538f014a046d9f6f1bb203d03ba08031aa8f1c9d2ff33e9b8','receipt_issue':294,'v1_r1_packaging_only_change':True,'scientific_results_unchanged':True,'package_checksum_verified_by_workflow':True})
 mech={'family':'D_SHOCK_FAILURE','definition':pre['fixed_csos_mechanism'],'candidate_catalog':pre['candidate_catalog'],'event_count':114,'chronology_rule':'failure is known only after the following M15 bar closes; entry is the first executable tick at or after that close','same_shock_reentry':'prohibited by original CSOS active-window suppression','session_boundary':'events may cross sessions; session is classified at entry','spread_and_execution':'Mid is never used as an executable price; LONG buys Ask/sells Bid, SHORT sells Bid/buys Ask'};write_json(a.out_dir/'shock_failure_mechanism_contract.json',mech)
 candcat={'candidates':pre['candidate_catalog'],'selection':pre['lofo_selection'],'portable_gate':pre['portable_gate']};write_json(a.out_dir/'candidate_catalog.json',candcat)
 (a.out_dir/'REPRODUCE.md').write_text('# Reproduction\n\nRun `.github/workflows/usdjpy_csos_shock_failure_phase2_v1.yml` on the frozen Research ref. The workflow downloads only 2023/2024 authorities, verifies digests, materializes the 1,882-trade baseline ledger, and invokes `tools/evaluate_usdjpy_csos_shock_failure_phase2_v1.py`.\n')
 receipt={'status':decision,'research_sha':a.research_sha,'core_sha':a.core_sha,'run_id':a.run_id,'2025_accessed':False,'csos_events':114,'reproduced_events':len(rep),'selected_candidate':selected,'source_digests':{k:v.get('sha256') for k,v in src.items() if isinstance(v,dict) and 'sha256' in v},'outputs':[]};write_json(a.out_dir/'execution_receipt.json',receipt)
 lines=['# USDJPY CSOS Shock Failure Phase 2','',f'**Decision: `{decision}`**','',f'- Selected fixed candidate: `{selected}`',f'- CSOS events reproduced: {len(rep)}/114',f'- Chronology: '+', '.join(f'{k}={v}' for k,v in chron.chronology_status.value_counts().to_dict().items()),f'- Observed-spread net: ¥{sm.net_profit_jpy:,.0f}',f'- PF: {sm.profit_factor:.3f}' if pd.notna(sm.profit_factor) else '- PF: undefined',f'- LOFO positive held-out folds: {heldpos}/4',f'- Weak-market net: ¥{comp.weak_market_net_jpy:,.0f}',f'- Corr B02/F05: {comp.correlation_to_B02:.3f} / {comp.correlation_to_F05:.3f}','', '## Gate checks','']+[f'- {k}: {v}' for k,v in gate_checks.items()]+['','## Boundaries','','No 2025 price or outcome was accessed. B02/F05 was not changed. Core, MT4 and production remain unauthorized.','', '## Interpretation','',('The family is blocked by source/chronology authority and must not be frozen.' if decision=='DATA_AUTHORITY_BLOCKED' else ('The candidate is portable enough to freeze for an implementation-contract stage, not production.' if decision=='PASS_PORTABLE_RESEARCH_CANDIDATE' else 'The pooled mechanism does not satisfy every portable gate and is retained only at the stated decision level.'))]
 (a.out_dir/'human_readable_report.md').write_text('\n'.join(lines)+'\n')
 # failure log for known operational issues is provided by workflow; initialize
 write_json(a.out_dir/'operational_failure_log.json',{'failures':[]})
 # manifest excluding itself; freeze receipt before hashing
 receipt=json.load(open(a.out_dir/'execution_receipt.json'));receipt['outputs']=sorted([p.name for p in a.out_dir.iterdir() if p.is_file() and p.name not in ('artifact_manifest.json','PACKAGE_SHA256SUMS')]);write_json(a.out_dir/'execution_receipt.json',receipt)
 files=[]
 for p in sorted(a.out_dir.iterdir()):
  if p.is_file() and p.name not in ('artifact_manifest.json','PACKAGE_SHA256SUMS'):
   files.append({'path':p.name,'bytes':p.stat().st_size,'sha256':sha256_file(p)})
 write_json(a.out_dir/'artifact_manifest.json',{'schema_version':'usdjpy_csos_shock_failure_phase2_manifest_v1','files':files})
 with (a.out_dir/'PACKAGE_SHA256SUMS').open('w') as f:
  for r in files+[{'path':'artifact_manifest.json','sha256':sha256_file(a.out_dir/'artifact_manifest.json')}]:f.write(f"{r['sha256']}  {r['path']}\n")
 print(json.dumps({'status':decision,'selected_candidate':selected,'events':len(rep),'unresolved_rate':unresolved,'contradiction_rate':contr},sort_keys=True))
if __name__=='__main__':main()

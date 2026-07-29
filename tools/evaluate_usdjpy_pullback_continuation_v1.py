#!/usr/bin/env python3
from __future__ import annotations
import argparse,gzip,hashlib,json,math
from collections import defaultdict
from pathlib import Path
import numpy as np,pandas as pd
from usdjpy_hyp034_bi5_source_v1 import iter_tick_days,m15_bars,source_inventory,tick_day_audit
HYP='USDJPY-HYP-035';FAM='S_PULLBACK_CONTINUATION_PORTABILITY';CAND='A_EXACT_EXECUTABLE_16BAR';VAR='J_PULLBACK_CONTINUATION'
PIP=.01;JPYPP=10.;CAP=1_000_000.;FOLDS=['2023H1','2023H2','2024H1','2024H2'];REPS=5000;SEED=35035;TOL=1e-6

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def clean(v):
 if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [clean(x) for x in v]
 if isinstance(v,np.integer):return int(v)
 if isinstance(v,(float,np.floating)):return None if not np.isfinite(v) else (0. if abs(v)<TOL else float(v))
 if isinstance(v,pd.Timestamp):return v.isoformat()
 return v
def wj(p,v):Path(p).write_text(json.dumps(clean(v),indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
def wg(p,d):
 raw=d.to_csv(index=False,lineterminator='\n',na_rep='',float_format='%.10f').encode()
 with Path(p).open('wb') as o:
  with gzip.GzipFile(filename='',mode='wb',fileobj=o,compresslevel=9,mtime=0) as z:z.write(raw)
def pf(s):
 s=np.asarray(s,float);gp=s[s>0].sum();gl=-s[s<0].sum();return None if gl<=TOL else float(gp/gl)
def dd(s,initial=CAP):
 e=initial+np.cumsum(np.asarray(s,float));
 if not len(e):return 0.,initial
 return float((np.maximum.accumulate(np.r_[initial,e])[1:]-e).max(initial=0)),float(np.r_[initial,e].min())
def fold(t):
 t=pd.Timestamp(t)
 if t<pd.Timestamp('2023-01-01',tz='UTC') or t>=pd.Timestamp('2025-01-01',tz='UTC'):return None
 return '2023H1' if t<pd.Timestamp('2023-07-01',tz='UTC') else '2023H2' if t<pd.Timestamp('2024-01-01',tz='UTC') else '2024H1' if t<pd.Timestamp('2024-07-01',tz='UTC') else '2024H2'
def sess(h):return 'TOKYO' if h<7 else 'LONDON' if h<12 else 'LONDON_NY_OVERLAP' if h<16 else 'NEW_YORK' if h<21 else 'TRANSITION'
def atlas(path):
 d=pd.read_csv(path);d=d[d.variant.eq(VAR)].copy()
 for c in ['signal_utc','entry_utc','exit_utc']:d[c]=pd.to_datetime(d[c],utc=True)
 d.side=d.side.astype(int);return d.sort_values(['signal_utc','side'],kind='mergesort').reset_index(drop=True)
def atlas_check(a):
 f=a.groupby('fold').normalized_pl_jpy.sum().reindex(FOLDS,fill_value=0);m=a.groupby(a.entry_utc.dt.strftime('%Y-%m')).normalized_pl_jpy.sum()
 r={'opportunities':len(a),'net_jpy':a.normalized_pl_jpy.sum(),'profit_factor':pf(a.normalized_pl_jpy),'positive_folds':int((f>0).sum()),'worst_fold_jpy':f.min(),'positive_months':int((m>0).sum()),'fold_net_jpy':f.to_dict(),'month_net_jpy':m.to_dict()}
 g={'count_1333':len(a)==1333,'net_exact':abs(r['net_jpy']-20751.999999999258)<=TOL,'pf_exact':abs(r['profit_factor']-1.1358533056633857)<=1e-12,'folds_4':r['positive_folds']==4,'worst_fold_exact':abs(r['worst_fold_jpy']-150.9999999995748)<=TOL};r['gates']=g;r['pass']=all(g.values());return r
def source(raw):
 audits=[];bars=[]
 for day in iter_tick_days(raw):
  audits.append(tick_day_audit(day));q=m15_bars(day)
  if len(q):bars.append(q)
 a=pd.DataFrame(audits);b=pd.concat(bars,ignore_index=True);b.bar_start_utc=pd.to_datetime(b.bar_start_utc,utc=True);b=b[(b.bar_start_utc>='2023-01-01')&(b.bar_start_utc<'2025-01-01')].sort_values('bar_start_utc').reset_index(drop=True);g=b.bar_start_utc.diff().dt.total_seconds()/60;inv=source_inventory(raw)
 r={'archive_count':inv['archive_count'],'archives':inv['archives'],'day_rows':len(a),'tick_count':int(a.tick_count.sum()),'ask_bid_inversion_count':int(a.ask_bid_inversion_count.sum()),'duplicate_timestamp_count':int(a.duplicate_timestamp_count.sum()),'nonmonotonic_timestamp_count':int(a.nonmonotonic_timestamp_count.sum()),'m15_bar_count':len(b),'duplicate_bar_count':int(b.bar_start_utc.duplicated().sum()),'missing_interval_count_gt_15m':int((g>15+TOL).sum()),'max_bar_gap_minutes':g.max(),'stable_duplicate_order':True,'unresolved_chronology':0}
 r['pass']=r['archive_count']==24 and r['ask_bid_inversion_count']==0 and r['nonmonotonic_timestamp_count']==0 and r['duplicate_bar_count']==0 and r['m15_bar_count']>60000;return b,a,r
def features(b):
 x=b.rename(columns={'bar_start_utc':'time','bid_open':'open','bid_high':'high','bid_low':'low','bid_close':'close'}).copy();pc=x.close.shift();tr=pd.concat([x.high-x.low,(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1);x['tr']=tr/PIP;x['a20']=x.tr.rolling(20).mean();x['e20']=x.close.ewm(span=20,adjust=False).mean();x['e96']=x.close.ewm(span=96,adjust=False).mean();x['ts']=(x.e20-x.e96)/(x.a20*PIP);x['tol']=.25*x.a20*PIP;x['fold']=x.time.map(fold);x['range_pips']=(x.high-x.low)/PIP;x['body_pips']=(x.close-x.open).abs()/PIP;x['close_loc']=(x.close-x.low)/(x.high-x.low).replace(0,np.nan);x['e20s4']=(x.e20-x.e20.shift(4))/PIP;x['e96s4']=(x.e96-x.e96.shift(4))/PIP;x['hi16']=x.high.shift().rolling(16).max();x['lo16']=x.low.shift().rolling(16).min();x['rg16']=x.hi16-x.lo16;return x
def signals(x):
 parts=[]
 for m,s,r in [((x.ts.shift()>=1)&(x.low<=x.e20+x.tol)&(x.close>x.e20)&(x.close>x.open),1,'uptrend_pullback'),((x.ts.shift()<=-1)&(x.high>=x.e20-x.tol)&(x.close<x.e20)&(x.close<x.open),-1,'downtrend_pullback')]:
  idx=x.index[pd.Series(m,index=x.index).fillna(False)]
  if len(idx):parts.append(pd.DataFrame({'i':idx,'side':s,'reason':r}))
 raw=pd.concat(parts,ignore_index=True).sort_values(['i','side']).drop_duplicates(['i','side']);active=-1;rows=[];sup={'raw':len(raw),'warmup':0,'tail':0,'fold_crossing':0,'active':0}
 for r in raw.itertuples(index=False):
  i=int(r.i)
  if i<100:sup['warmup']+=1;continue
  if i+17>=len(x):sup['tail']+=1;continue
  if x.fold.iat[i]!=x.fold.iat[i+17]:sup['fold_crossing']+=1;continue
  if i<=active:sup['active']+=1;continue
  active=i+17;e=x.iloc[i+1];q=x.iloc[i+17];a=x.iloc[i];rows.append({'raw_event_id':f'{a.fold}|{VAR}|{e.time.isoformat()}|{int(r.side)}','signal_index':i,'fold':a.fold,'reason':r.reason,'signal_utc':a.time,'decision_utc':a.time+pd.Timedelta('15min'),'entry_boundary_utc':e.time,'exit_boundary_utc':q.time,'side':int(r.side),'side_label':'LONG' if r.side>0 else 'SHORT','session':sess(e.time.hour),'entry_bar_bid_open':e.open,'entry_bar_ask_open':e.ask_open,'exit_bar_bid_open':q.open,'exit_bar_ask_open':q.ask_open})
 return pd.DataFrame(rows),sup
def identity(a,r):
 a=a.copy();r=r.copy();a['sk']=a.signal_utc.astype(str)+'|'+a.side.astype(str);r['sk']=r.signal_utc.astype(str)+'|'+r.side.astype(str);a['ek']=a.sk+'|'+a.entry_utc.astype(str)+'|'+a.exit_utc.astype(str);r['ek']=r.sk+'|'+r.entry_boundary_utc.astype(str)+'|'+r.exit_boundary_utc.astype(str);A=set(a.sk);R=set(r.sk);AE=set(a.ek);RE=set(r.ek);rows=[]
 for k in sorted(A-R):
  z=a[a.sk.eq(k)].iloc[0];same=r[r.signal_utc.eq(z.signal_utc)];rows.append({'classification':'SIDE_MISMATCH' if len(same) else 'ATLAS_ONLY','signal_utc':z.signal_utc,'side':z.side,'detail':'same timestamp opposite side' if len(same) else 'no raw signal'})
 for k in sorted(R-A):
  z=r[r.sk.eq(k)].iloc[0];same=a[a.signal_utc.eq(z.signal_utc)];rows.append({'classification':'SIDE_MISMATCH_RAW' if len(same) else 'RAW_ONLY','signal_utc':z.signal_utc,'side':z.side,'detail':'same timestamp opposite side' if len(same) else 'no Atlas signal'})
 ai=a.set_index('sk');ri=r.set_index('sk');bound=plm=0
 for k in sorted(A&R):
  u=ai.loc[k];v=ri.loc[k];u=u.iloc[0] if isinstance(u,pd.DataFrame) else u;v=v.iloc[0] if isinstance(v,pd.DataFrame) else v;em=pd.Timestamp(u.entry_utc)!=pd.Timestamp(v.entry_boundary_utc);xm=pd.Timestamp(u.exit_utc)!=pd.Timestamp(v.exit_boundary_utc);bound+=em or xm;raw=int(v.side)*(v.exit_bar_bid_open-v.entry_bar_bid_open)/PIP-.5;plm+=abs(raw*JPYPP-u.normalized_pl_jpy)>TOL
 union=len(A|R);o={'atlas_opportunities':len(a),'raw_native_opportunities':len(r),'common_signal_side_events':len(A&R),'common_exact_events':len(AE&RE),'atlas_only_events':len(A-R),'raw_only_events':len(R-A),'side_mismatches':sum(str(z['classification']).startswith('SIDE') for z in rows),'entry_exit_boundary_mismatches':int(bound),'bid_open_pl_mismatches':int(plm),'signal_side_match_rate':len(A&R)/len(A),'exact_event_identity_match_rate':len(AE&RE)/len(AE),'material_contradiction_rate':len(A^R)/union,'all_mismatches_classified':True,'unfavorable_mismatch_excluded':False};return o,pd.DataFrame(rows)
def execute(raw,e):
 e=e.copy();targets=defaultdict(list);state={}
 for i,r in e.iterrows():
  s=int(pd.Timestamp(r.entry_boundary_utc).value);x=int(pd.Timestamp(r.exit_boundary_utc).value);state[i]={'entry':None,'e5':None,'e15':None,'exit':None,'best':None,'worst':None,'best_ns':None,'worst_ns':None,'marks':{}}
  for d in pd.date_range(pd.Timestamp(r.entry_boundary_utc).normalize(),pd.Timestamp(r.exit_boundary_utc).normalize(),freq='D'):targets[d.strftime('%Y-%m-%d')].append(i)
 for day in iter_tick_days(raw):
  if day.empty or day.date_utc not in targets:continue
  t=day.timestamp_ns
  for i in targets[day.date_utc]:
   r=e.loc[i];s=int(pd.Timestamp(r.entry_boundary_utc).value);x=int(pd.Timestamp(r.exit_boundary_utc).value);st=state[i]
   for name,z in [('entry',s),('e5',s+5_000_000_000),('e15',s+15_000_000_000),('exit',x)]:
    if st[name] is None:
     p=int(np.searchsorted(t,z,'left'))
     if p<len(t):st[name]=(int(t[p]),float(day.bid[p]),float(day.ask[p]))
   for h in [15,30,60,120,240]:
    if h not in st['marks']:
     p=int(np.searchsorted(t,s+h*60_000_000_000,'left'))
     if p<len(t):st['marks'][h]=(int(t[p]),float(day.bid[p]),float(day.ask[p]))
   lo=int(np.searchsorted(t,s,'left'));hi=int(np.searchsorted(t,x,'left'));hi=min(hi+(hi<len(t)),len(t))
   if lo<hi:
    p=day.bid[lo:hi] if r.side>0 else day.ask[lo:hi];tt=t[lo:hi];bp=int(np.argmax(p) if r.side>0 else np.argmin(p));wp=int(np.argmin(p) if r.side>0 else np.argmax(p));b=float(p[bp]);w=float(p[wp])
    if st['best'] is None or (b>st['best'] if r.side>0 else b<st['best']):st['best']=b;st['best_ns']=int(tt[bp])
    if st['worst'] is None or (w<st['worst'] if r.side>0 else w>st['worst']):st['worst']=w;st['worst_ns']=int(tt[wp])
 rows=[]
 for i,r in e.iterrows():
  st=state[i];z=r.to_dict();resolved=all(st[k] is not None for k in ['entry','e5','e15','exit']);z['chronology_resolved']=resolved
  if not resolved:rows.append(z);continue
  for k in ['entry','e5','e15','exit']:
   z[k+'_tick_utc']=pd.Timestamp(st[k][0],tz='UTC');z[k+'_bid']=st[k][1];z[k+'_ask']=st[k][2]
  side=r.side;ep=st['entry'][2] if side>0 else st['entry'][1];xp=st['exit'][1] if side>0 else st['exit'][2];e5=st['e5'][2] if side>0 else st['e5'][1];e15=st['e15'][2] if side>0 else st['e15'][1];z['entry_price']=ep;z['exit_price']=xp;z['observed_pips']=side*(xp-ep)/PIP;z['realized_pl_jpy']=z['observed_pips']*JPYPP;z['entry_delay_5s_pl_jpy']=side*(xp-e5)/PIP*JPYPP;z['entry_delay_15s_pl_jpy']=side*(xp-e15)/PIP*JPYPP;z['spread_pips']=(st['entry'][2]-st['entry'][1])/PIP;z['mfe_pips']=(st['best']-ep)/PIP if side>0 else (ep-st['best'])/PIP;z['mae_pips']=(st['worst']-ep)/PIP if side>0 else (ep-st['worst'])/PIP;z['time_to_mfe_seconds']=(st['best_ns']-st['entry'][0])/1e9;z['time_to_mae_seconds']=(st['worst_ns']-st['entry'][0])/1e9;z['entry_exec_delay_seconds']=(st['entry'][0]-int(pd.Timestamp(r.entry_boundary_utc).value))/1e9;z['exit_exec_delay_seconds']=(st['exit'][0]-int(pd.Timestamp(r.exit_boundary_utc).value))/1e9
  for h,m in st['marks'].items():mp=m[1] if side>0 else m[2];z[f'return_{h}m_pips']=side*(mp-ep)/PIP
  z['spread_plus_0_5_pl_jpy']=z['realized_pl_jpy']-5;z['spread_plus_1_0_pl_jpy']=z['realized_pl_jpy']-10;z['spread_plus_2_0_pl_jpy']=z['realized_pl_jpy']-20;z['slippage_0_5_each_pl_jpy']=z['realized_pl_jpy']-10;z['severe_case_pl_jpy']=z['entry_delay_15s_pl_jpy']-30;rows.append(z)
 return pd.DataFrame(rows)
def mechanism(x,d):
 rows=[]
 for r in d.itertuples(index=False):
  b=x.iloc[r.signal_index];p=x.iloc[r.signal_index-1];side=r.side;near=x.iloc[max(0,r.signal_index-8):r.signal_index+1];around=((near.low<=near.e20+near.tol)&(near.high>=near.e20-near.tol)).sum();pb=0
  for j in range(r.signal_index-1,max(-1,r.signal_index-17),-1):
   if j<0 or np.sign(x.close.iat[j]-x.open.iat[j])!=-side:break
   pb+=1
  extreme=b.hi16 if side>0 else b.lo16;dist=side*(extreme-b.close)/PIP;depth=(b.e20-b.low)/PIP if side>0 else (b.high-b.e20)/PIP;rows.append({'raw_event_id':r.raw_event_id,'fold':r.fold,'side':side,'signal_utc':r.signal_utc,'ema20':b.e20,'reference_slow_ema96':b.e96,'ema_separation_pips':(b.e20-b.e96)/PIP,'separation_atr_ratio':b.ts,'ema20_slope_4_pips':b.e20s4,'ema96_slope_4_pips':b.e96s4,'trend_direction':'UP' if side>0 else 'DOWN','trend_age_bars':None,'consecutive_trend_bars':None,'distance_from_pre_pullback_extreme_pips':dist,'completed_h1_state':'UP' if x.close.iloc[max(0,r.signal_index-4):r.signal_index+1].iloc[-1]>x.close.iloc[max(0,r.signal_index-4):r.signal_index+1].iloc[0] else 'DOWN','completed_h4_state':'UP' if x.close.iloc[max(0,r.signal_index-16):r.signal_index+1].iloc[-1]>x.close.iloc[max(0,r.signal_index-16):r.signal_index+1].iloc[0] else 'DOWN','depth_to_ema20_pips':depth,'ema20_touch_or_cross':True,'time_spent_around_ema20_bars':int(around),'pullback_duration_bars':pb,'pullback_bar_count':pb,'retracement_ratio':abs(extreme-b.close)/b.rg16 if b.rg16>0 else None,'pullback_volatility_atr20_pips':b.a20,'adverse_spread_at_pullback_pips':b.spread_max_pips,'confirmation_body_pips':b.body_pips,'confirmation_range_pips':b.range_pips,'confirmation_close_location':b.close_loc,'confirmation_close_relative_ema20_pips':side*(b.close-b.e20)/PIP,'confirmation_close_relative_prior_bar_pips':side*(b.close-p.close)/PIP,'tick_velocity_ticks_per_second':b.tick_count/900,'time_from_pullback_to_confirmation_bars':pb,'first_executable_spread_pips':r.spread_pips,'mae_pips':r.mae_pips,'mfe_pips':r.mfe_pips,'time_to_mae_seconds':r.time_to_mae_seconds,'time_to_mfe_seconds':r.time_to_mfe_seconds,'return_15m_pips':r.return_15m_pips,'return_30m_pips':r.return_30m_pips,'return_60m_pips':r.return_60m_pips,'return_120m_pips':r.return_120m_pips,'return_240m_pips':r.return_240m_pips,'new_trend_extreme_reach':r.mfe_pips>max(0,dist),'ema20_recross':r.mae_pips<-abs(depth),'continuation_failure':r.realized_pl_jpy<=0,'fixed_exit_pl_jpy':r.realized_pl_jpy})
 return pd.DataFrame(rows)
def metrics(d):
 g=d.sort_values('exit_tick_utc');f=g.groupby('fold').realized_pl_jpy.agg(['count','sum']).reindex(FOLDS,fill_value=0);m=g.groupby(pd.to_datetime(g.entry_tick_utc,utc=True).dt.strftime('%Y-%m')).realized_pl_jpy.sum();s=g.groupby('side_label').realized_pl_jpy.agg(['count','sum']).reindex(['LONG','SHORT'],fill_value=0);md,mn=dd(g.realized_pl_jpy);return {'trades':len(g),'net_jpy':g.realized_pl_jpy.sum(),'profit_factor':pf(g.realized_pl_jpy),'win_rate':(g.realized_pl_jpy>0).mean(),'median_pl_jpy':g.realized_pl_jpy.median(),'mdd_jpy':md,'minimum_equity_jpy':mn,'positive_folds':int((f['sum']>0).sum()),'minimum_fold_net_jpy':f['sum'].min(),'positive_months':int((m>0).sum()),'fold_results':f.to_dict('index'),'month_results':m.to_dict(),'side_results':s.to_dict('index'),'mean_mae_pips':g.mae_pips.mean(),'mean_mfe_pips':g.mfe_pips.mean(),'median_mae_pips':g.mae_pips.median(),'median_mfe_pips':g.mfe_pips.median(),'mean_spread_pips':g.spread_pips.mean(),'max_entry_delay_seconds':g.entry_exec_delay_seconds.max(),'max_exit_delay_seconds':g.exit_exec_delay_seconds.max()}
def bucket(d,key):
 rows=[]
 for k,g in d.groupby(key):
  md,mn=dd(g.sort_values('exit_tick_utc').realized_pl_jpy);m=g.groupby(pd.to_datetime(g.entry_tick_utc,utc=True).dt.strftime('%Y-%m')).realized_pl_jpy.sum();rows.append({key:k,'trades':len(g),'net_jpy':g.realized_pl_jpy.sum(),'profit_factor':pf(g.realized_pl_jpy),'win_rate':(g.realized_pl_jpy>0).mean(),'median_pl_jpy':g.realized_pl_jpy.median(),'mdd_jpy':md,'minimum_equity_jpy':mn,'mean_mae_pips':g.mae_pips.mean(),'mean_mfe_pips':g.mfe_pips.mean(),'positive_months':int((m>0).sum()),'mean_spread_pips':g.spread_pips.mean(),'entry_delay_5s_net_jpy':g.entry_delay_5s_pl_jpy.sum(),'entry_delay_15s_net_jpy':g.entry_delay_15s_pl_jpy.sum()})
 return pd.DataFrame(rows)
def concentration(d):
 v=d.realized_pl_jpy.sort_values(ascending=False);w=v[v>0];n=math.ceil(len(w)*.1);fp=d.groupby('fold').realized_pl_jpy.sum();fp=fp[fp>0];mp=d.groupby(pd.to_datetime(d.entry_tick_utc,utc=True).dt.strftime('%Y-%m')).realized_pl_jpy.sum();mp=mp[mp>0];sp=d.groupby('session').realized_pl_jpy.sum();sp=sp[sp>0];net=v.sum();return {'best_event_excluded_net_jpy':net-v.head(1).sum(),'top3_events_excluded_net_jpy':net-v.head(3).sum(),'top5_events_excluded_net_jpy':net-v.head(5).sum(),'top_decile_winner_count':n,'top_decile_winners_excluded_net_jpy':net-w.head(n).sum(),'largest_positive_fold_share':fp.max()/fp.sum(),'largest_positive_month_share':mp.max()/mp.sum(),'largest_positive_session_share':sp.max()/sp.sum()}
def bootstrap(d):
 rng=np.random.default_rng(SEED)
 def one(a):
  z=rng.choice(a,size=(REPS,len(a)),replace=True).sum(1);return {'lower_95_jpy':np.quantile(z,.025),'median_jpy':np.median(z),'p_nonpositive':(z<=0).mean()}
 event=d.realized_pl_jpy.to_numpy();date=d.groupby(pd.to_datetime(d.entry_tick_utc,utc=True).dt.strftime('%Y-%m-%d')).realized_pl_jpy.sum().to_numpy();block=d.groupby([pd.to_datetime(d.entry_tick_utc,utc=True).dt.strftime('%Y-%m-%d'),d.session]).realized_pl_jpy.sum().to_numpy();return {'reps':REPS,'seed':SEED,'event':one(event),'date':one(date),'session_block':one(block)}
def portfolio(path,d):
 b=pd.read_csv(path);b.entry_utc=pd.to_datetime(b.entry_utc,utc=True);b.close_utc=pd.to_datetime(b.close_utc,utc=True);idx=pd.Index(sorted(set(b.entry_utc.dt.strftime('%Y-%m-%d'))|set(d.entry_tick_utc.dt.strftime('%Y-%m-%d'))));series=lambda q,t,c:q.groupby(pd.to_datetime(q[t],utc=True).dt.strftime('%Y-%m-%d'))[c].sum().reindex(idx,fill_value=0.);base=series(b,'entry_utc','realized_pl_jpy');cand=series(d,'entry_tick_utc','realized_pl_jpy');b02=series(b[b.strategy.eq('B02')],'entry_utc','realized_pl_jpy');f05=series(b[b.strategy.eq('F05')],'entry_utc','realized_pl_jpy');corr=lambda a,z:0. if a.std()==0 or z.std()==0 else a.corr(z);events=sorted([(r.close_utc,r.realized_pl_jpy) for r in b.itertuples()]+[(r.exit_tick_utc,r.realized_pl_jpy) for r in d.itertuples()]);bm,bmin=dd(b.sort_values('close_utc').realized_pl_jpy);cm,cmin=dd([z[1] for z in events]);business=pd.date_range('2023-01-02','2024-12-31',freq='B',tz='UTC').strftime('%Y-%m-%d');cluster=lambda s,n:s.reindex(business,fill_value=0).rolling(n,min_periods=n).sum().min();return {'status':'DIAGNOSTIC_AFTER_STANDALONE_STOP','baseline_net_jpy':b.realized_pl_jpy.sum(),'candidate_net_jpy':d.realized_pl_jpy.sum(),'combined_net_jpy':b.realized_pl_jpy.sum()+d.realized_pl_jpy.sum(),'correlation_to_B02':corr(cand,b02),'correlation_to_F05':corr(cand,f05),'negative_baseline_day_candidate_contribution_jpy':cand[base<0].sum(),'positive_baseline_day_candidate_contribution_jpy':cand[base>0].sum(),'baseline_realized_dd_jpy':bm,'combined_realized_dd_jpy':cm,'baseline_minimum_realized_equity_jpy':bmin,'combined_minimum_realized_equity_jpy':cmin,'baseline_worst_5_business_day_jpy':cluster(base,5),'combined_worst_5_business_day_jpy':cluster(base+cand,5),'baseline_worst_20_business_day_jpy':cluster(base,20),'combined_worst_20_business_day_jpy':cluster(base+cand,20),'baseline_trade_outcome_changed':False,'full_equity_status':'NOT_REACHED_BECAUSE_EARLIER_BINDING_STOP'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--raw-2023',type=Path,required=True);ap.add_argument('--raw-2024',type=Path,required=True);ap.add_argument('--atlas-ledger',type=Path,required=True);ap.add_argument('--baseline-trades',type=Path,required=True);ap.add_argument('--baseline-states',type=Path);ap.add_argument('--prereg',type=Path,required=True);ap.add_argument('--source-manifest',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);ap.add_argument('--research-sha',required=True);ap.add_argument('--core-sha',required=True);ap.add_argument('--run-id',required=True);ap.add_argument('--preflight-only',action='store_true');z=ap.parse_args();z.out_dir.mkdir(parents=True,exist_ok=True);pre=json.load(open(z.prereg));man=json.load(open(z.source_manifest));assert pre['status']=='FROZEN_BEFORE_DEVELOPMENT_OUTCOMES' and pre['hypothesis_id']==HYP and pre['fixed_atlas_contract']['hold_bars']==16 and man['forbidden_assets']==['2019','2020','2021','2022','2025']
 if z.preflight_only:
  r={'schema_version':'usdjpy_hyp035_preflight_receipt_v1','status':'PASS_NO_SOURCE_NATIVE_OUTCOMES','hypothesis_id':HYP,'family_id':FAM,'candidate_id':CAND,'raw_archive_count':len(list(z.raw_2023.glob('*.tar.gz')))+len(list(z.raw_2024.glob('*.tar.gz'))),'atlas_ledger_exists':z.atlas_ledger.exists(),'baseline_ledger_exists':z.baseline_trades.exists(),'candidate_outcome_computed':False,'protected_2020_2022_accessed':False,'protected_2025_accessed':False};r['pass']=r['raw_archive_count']==24 and r['atlas_ledger_exists'] and r['baseline_ledger_exists'];wj(z.out_dir/'preflight_receipt.json',r);print(json.dumps(r,indent=2));return 0 if r['pass'] else 2
 gates=[];add=lambda st,g:gates.extend({'stage':st,'gate':k,'pass':bool(v)} for k,v in g.items());decision=stage=None;a=atlas(z.atlas_ledger);ar=atlas_check(a);add('ATLAS_AUTHORITY',ar['gates']);
 if not ar['pass']:decision='FAIL_ATLAS_IDENTITY';stage='ATLAS_AUTHORITY'
 if decision is None:
  b,audit,src=source([z.raw_2023,z.raw_2024]);wg(z.out_dir/'source_tick_day_audit.csv.gz',audit);wj(z.out_dir/'source_inventory.json',src);sg={'archive_count_24':src['archive_count']==24,'ask_bid_inversion_zero':src['ask_bid_inversion_count']==0,'nonmonotonic_zero':src['nonmonotonic_timestamp_count']==0,'duplicate_bar_zero':src['duplicate_bar_count']==0,'m15_population':src['m15_bar_count']>60000};add('SOURCE_AUTHORITY',sg)
  if not all(sg.values()):decision='FAIL_SOURCE_AUTHORITY';stage='SOURCE_AUTHORITY'
 else:b=None;src={'status':'NOT_EXECUTED'}
 ident={'status':'NOT_EXECUTED'};sup={};d=None;stand={'status':'NOT_EXECUTED'};conc={'status':'NOT_EXECUTED'};boot={'status':'NOT_EXECUTED'};rob={'status':'NOT_EXECUTED'};port={'status':'NOT_EXECUTED'}
 if decision is None:
  x=features(b);r,sup=signals(x);ident,mm=identity(a,r);wg(z.out_dir/'atlas_raw_native_mismatch_ledger.csv.gz',mm);wj(z.out_dir/'atlas_identity_result.json',{'identity':ident,'suppression':sup});ig={'exact_identity_ge_95pct':ident['exact_event_identity_match_rate']>=.95,'all_mismatches_classified':True,'material_contradiction_le_5pct':ident['material_contradiction_rate']<=.05,'no_selective_exclusion':True};add('EVENT_IDENTITY',ig)
  if not all(ig.values()):decision='FAIL_ATLAS_IDENTITY';stage='EVENT_IDENTITY'
 if decision is None:
  d=execute([z.raw_2023,z.raw_2024],r);integrity={'unresolved_chronology_zero':int((~d.chronology_resolved).sum())==0,'duplicate_event_zero':int(d.raw_event_id.duplicated().sum())==0,'lookahead_zero':(d.entry_tick_utc>=d.decision_utc).all(),'currency_mismatch_zero':True,'replay_mismatch_zero':np.allclose(d.realized_pl_jpy,d.observed_pips*JPYPP,atol=TOL)};add('EXECUTABLE_INTEGRITY',integrity)
  if not all(integrity.values()):decision='TECHNICAL_NO_RESULT';stage='EXECUTABLE_CHRONOLOGY'
 if decision is None:
  mech=mechanism(x,d);wg(z.out_dir/'source_native_executable_ledger.csv.gz',d);wg(z.out_dir/'mechanism_audit.csv.gz',mech);d['month']=d.entry_tick_utc.dt.strftime('%Y-%m');
  for k in ['side_label','fold','month','session']:bucket(d,k).to_csv(z.out_dir/f'{k}_metrics.csv',index=False)
  stand=metrics(d);sample={'resolved_ge_1000':stand['trades']>=1000,'each_fold_ge_200':all(v['count']>=200 for v in stand['fold_results'].values()),'long_ge_200':stand['side_results']['LONG']['count']>=200,'short_ge_200':stand['side_results']['SHORT']['count']>=200,'fold_crossing_zero':True};econ={'net_positive':stand['net_jpy']>0,'pf_ge_1_10':(stand['profit_factor'] or 0)>=1.10,'folds_4_of_4':stand['positive_folds']==4,'minimum_fold_nonnegative':stand['minimum_fold_net_jpy']>=-TOL,'positive_months_ge_16':stand['positive_months']>=16,'mdd_within_ceiling':stand['mdd_jpy']<=15758.75+TOL,'minimum_equity_above_floor':stand['minimum_equity_jpy']>=984241.25-TOL};add('SAMPLE',sample);add('STANDALONE_ECONOMICS',econ);port=portfolio(z.baseline_trades,d)
  if not all(sample.values()) or not all(econ.values()):decision='NO_PORTABLE_EXECUTABLE_CANDIDATE';stage='DEVELOPMENT_STANDALONE'
 if decision is None:
  conc=concentration(d);cg={'best_event_excluded_positive':conc['best_event_excluded_net_jpy']>0,'top3_excluded_positive':conc['top3_events_excluded_net_jpy']>0,'top5_excluded_positive':conc['top5_events_excluded_net_jpy']>0,'top_decile_excluded_positive':conc['top_decile_winners_excluded_net_jpy']>0,'fold_share_le_50pct':conc['largest_positive_fold_share']<=.5,'month_share_le_20pct':conc['largest_positive_month_share']<=.2,'session_share_le_60pct':conc['largest_positive_session_share']<=.6};add('CONCENTRATION',cg)
  if not all(cg.values()):decision='NO_PORTABLE_EXECUTABLE_CANDIDATE';stage='DEVELOPMENT_CONCENTRATION'
 if decision is None:
  boot=bootstrap(d);bg={'event_lower_positive':boot['event']['lower_95_jpy']>0,'date_lower_positive':boot['date']['lower_95_jpy']>0,'session_lower_positive':boot['session_block']['lower_95_jpy']>0,'event_p_le_5pct':boot['event']['p_nonpositive']<=.05,'date_p_le_5pct':boot['date']['p_nonpositive']<=.05,'session_p_le_5pct':boot['session_block']['p_nonpositive']<=.05};add('RESAMPLING',bg)
  if not all(bg.values()):decision='NO_PORTABLE_EXECUTABLE_CANDIDATE';stage='DEVELOPMENT_RESAMPLING'
 if decision is None:
  rob={'observed_bid_ask_net_jpy':d.realized_pl_jpy.sum(),'spread_plus_0_5_pip_net_jpy':d.spread_plus_0_5_pl_jpy.sum(),'spread_plus_1_0_pip_net_jpy':d.spread_plus_1_0_pl_jpy.sum(),'spread_plus_2_0_pip_net_jpy':d.spread_plus_2_0_pl_jpy.sum(),'entry_delay_5s_net_jpy':d.entry_delay_5s_pl_jpy.sum(),'entry_delay_15s_net_jpy':d.entry_delay_15s_pl_jpy.sum(),'adverse_slippage_0_5_each_net_jpy':d.slippage_0_5_each_pl_jpy.sum(),'severe_case_net_jpy':d.severe_case_pl_jpy.sum()};rg={k:rob[k]>0 for k in ['observed_bid_ask_net_jpy','spread_plus_0_5_pip_net_jpy','spread_plus_1_0_pip_net_jpy','entry_delay_5s_net_jpy','entry_delay_15s_net_jpy','adverse_slippage_0_5_each_net_jpy']};add('EXECUTION_ROBUSTNESS',rg)
  if not all(rg.values()):decision='NO_PORTABLE_EXECUTABLE_CANDIDATE';stage='DEVELOPMENT_EXECUTION_ROBUSTNESS'
 if decision is None:decision='TECHNICAL_NO_RESULT';stage='DEVELOPMENT_PORTFOLIO_FULL_EQUITY_AUTHORITY';add('PORTFOLIO',{'full_equity_authority_available':False})
 gf=pd.DataFrame(gates);gf.to_csv(z.out_dir/'candidate_gate_matrix.csv',index=False);wj(z.out_dir/'atlas_contract_extraction.json',{'fixed_contract':pre['fixed_atlas_contract'],'authority':pre['starting_authority'],'reproduction':ar});wj(z.out_dir/'standalone_metrics.json',stand);wj(z.out_dir/'concentration.json',conc);wj(z.out_dir/'bootstrap.json',boot);wj(z.out_dir/'execution_robustness.json',rob);wj(z.out_dir/'portfolio_diagnostics.json',port);failed=gf[~gf['pass']]
 result={'schema_version':'usdjpy_hyp035_development_result_v1','status':'COMPLETE_AT_FIRST_BINDING_STOP','hypothesis_id':HYP,'family_id':FAM,'candidate_id':CAND,'decision':decision,'failed_binding_stage':stage,'failed_binding_gates':failed[['stage','gate']].to_dict('records'),'research_start_sha':pre['starting_authority']['research_main_sha'],'research_execution_sha':z.research_sha,'core_start_sha':pre['starting_authority']['core_main_sha'],'core_end_sha':z.core_sha,'run_id':z.run_id,'atlas':ar,'source_authority':src,'atlas_identity':ident,'suppression':sup,'source_native_trades':0 if d is None else len(d),'standalone':stand,'concentration':conc,'bootstrap':boot,'execution_robustness':rob,'portfolio':port,'candidate_freeze':False,'historical_2020_2022_authorized':False,'historical_2020_2022_accessed':False,'core_mt4_authorized':False,'core_modified':False,'mt4_executed':False,'external_2025h1_authorized':False,'protected_2025_accessed':False,'production_authorized':False,'live_authorized':False,'no_retuning':True};wj(z.out_dir/'final_result.json',result);wj(z.out_dir/'candidate_registry.json',{'schema_version':'usdjpy_hyp035_candidate_registry_v1','hypothesis_id':HYP,'family_id':FAM,'candidate_ids':[CAND],'selected_candidate':None,'candidate_freeze':False,'decision':decision,'failed_binding_stage':stage,'historical_2020_2022_authorized':False,'core_mt4_authorized':False,'2025_authorized':False,'production_authorized':False,'live_authorized':False,'no_retuning':True});wj(z.out_dir/'period_access_receipt.json',{'development_2023_2024_accessed':True,'historical_2020_2022_accessed':False,'protected_2025h1_accessed':False,'protected_2025h2_accessed':False,'reason':f'Stopped at {stage}'});wj(z.out_dir/'currency_audit.json',{'status':'PASS_DEVELOPMENT_JPY_CONTRACT',**pre['monetary_contract'],'currency_mismatch_count':0 if d is not None else None});(z.out_dir/z.prereg.name).write_bytes(z.prereg.read_bytes());(z.out_dir/z.source_manifest.name).write_bytes(z.source_manifest.read_bytes());(z.out_dir/'human_report.md').write_text(f'# USDJPY-HYP-035 Pullback Continuation Development Result\n\nDecision: `{decision}`\n\nFirst binding stop: `{stage}`\n\nAtlas opportunities: {ar["opportunities"]}. Raw-native opportunities: {ident.get("raw_native_opportunities")}. Source-native trades: {result["source_native_trades"]}. Net JPY: {stand.get("net_jpy")}. PF: {stand.get("profit_factor")}. Positive folds: {stand.get("positive_folds")}. Positive months: {stand.get("positive_months")}. MDD JPY: {stand.get("mdd_jpy")}. Minimum equity JPY: {stand.get("minimum_equity_jpy")}.\n\n2020-2022, Core/MT4 and 2025 were not accessed. No rescue or retuning was performed.\n',encoding='utf-8')
 files=[]
 for p in sorted(z.out_dir.iterdir()):
  if p.is_file() and p.name not in ['artifact_manifest.json','PACKAGE_SHA256SUMS']:files.append({'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
 wj(z.out_dir/'artifact_manifest.json',{'schema_version':'usdjpy_hyp035_artifact_manifest_v1','hypothesis_id':HYP,'decision':decision,'files':files,'protected_2020_2022_accessed':False,'protected_2025_accessed':False});files.append({'path':'artifact_manifest.json','sha256':sha(z.out_dir/'artifact_manifest.json')});(z.out_dir/'PACKAGE_SHA256SUMS').write_text(''.join(f'{r["sha256"]}  {r["path"]}\n' for r in files));print(json.dumps(clean({'decision':decision,'failed_binding_stage':stage,'source_native_trades':result['source_native_trades'],'net_jpy':stand.get('net_jpy'),'profit_factor':stand.get('profit_factor'),'positive_months':stand.get('positive_months')}),indent=2));return 0
if __name__=='__main__':raise SystemExit(main())

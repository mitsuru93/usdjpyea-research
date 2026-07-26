#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,math
from datetime import datetime,timedelta,timezone
from pathlib import Path
import numpy as np,pandas as pd
PIP=.01;COST=.5;JPYPP=10.;FOLDS=['2023H1','2023H2','2024H1','2024H2'];FAMS=list('ABCDEFGHIJK')
NAMES={'A':'False Breakout Reversal','B':'Balance Mean Reversion','C':'Shock Continuation','D':'Shock Failure','E':'Session Transition','F':'Liquidity Sweep','G':'Trend Exhaustion','H':'Volatility Compression Breakout','I':'Failed Trend Continuation','J':'Pullback Continuation','K':'Other Literature- and Practice-Led Families'}
V2F={'A_FALSE_BREAKOUT_REVERSAL':'A','B_BALANCE_MEAN_REVERSION':'B','C_SHOCK_CONTINUATION':'C','D_SHOCK_FAILURE':'D','E_TOKYO_LONDON':'E','E_LONDON_NY':'E','E_NY_TOKYO':'E','F_PREVIOUS_DAY_SWEEP':'F','F_ASIAN_RANGE_SWEEP':'F','G_TREND_EXHAUSTION':'G','H_COMPRESSION_BREAKOUT':'H','I_FAILED_TREND_CONTINUATION':'I','J_PULLBACK_CONTINUATION':'J','K_LONDON_OPENING_RANGE_BREAKOUT':'K','K_ROUND_NUMBER_REJECTION':'K','K_DAILY_TIME_SERIES_MOMENTUM':'K'}
HOLD={'A_FALSE_BREAKOUT_REVERSAL':16,'B_BALANCE_MEAN_REVERSION':16,'C_SHOCK_CONTINUATION':8,'D_SHOCK_FAILURE':8,'E_TOKYO_LONDON':8,'E_LONDON_NY':8,'E_NY_TOKYO':8,'F_PREVIOUS_DAY_SWEEP':12,'F_ASIAN_RANGE_SWEEP':12,'G_TREND_EXHAUSTION':12,'H_COMPRESSION_BREAKOUT':16,'I_FAILED_TREND_CONTINUATION':12,'J_PULLBACK_CONTINUATION':16,'K_LONDON_OPENING_RANGE_BREAKOUT':8,'K_ROUND_NUMBER_REJECTION':12,'K_DAILY_TIME_SERIES_MOMENTUM':32}
SIMPLE={'A':92,'B':86,'C':90,'D':88,'E':84,'F':90,'G':82,'H':91,'I':80,'J':87,'K':86}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def sunday(y,m,n,h):
 d=datetime(y,m,1,h,tzinfo=timezone.utc);return pd.Timestamp(d+timedelta(days=(6-d.weekday())%7+7*(n-1)))
def histutc(t):
 w=t-pd.Timedelta(hours=2);return t-pd.Timedelta(hours=3) if sunday(t.year,3,2,7)<=w<sunday(t.year,11,1,6) else w
def finish(d):
 x=d.sort_values('time').drop_duplicates('time').reset_index(drop=True);assert len(x) and x.time.is_monotonic_increasing
 x['fold']=np.select([x.time<pd.Timestamp('2023-07-01',tz='UTC'),x.time<pd.Timestamp('2024-01-01',tz='UTC'),x.time<pd.Timestamp('2024-07-01',tz='UTC')],FOLDS[:3],default='2024H2');x['date']=x.time.dt.strftime('%Y-%m-%d');x['hour']=x.time.dt.hour;x['minute']=x.time.dt.minute;return x
def bars23(p):
 d=pd.read_csv(p);req={'timestamp_utc','open','high','low','close'};assert req<=set(d)
 if 'first_timestamp_mt4_server' in d: t=pd.DatetimeIndex([histutc(z) for z in pd.to_datetime(d.first_timestamp_mt4_server,utc=True)])
 else:t=pd.to_datetime(d.timestamp_utc,utc=True)
 q=pd.DataFrame({'time':t,'open':d.open,'high':d.high,'low':d.low,'close':d.close});q=q[(q.time>=pd.Timestamp('2023-01-01',tz='UTC'))&(q.time<pd.Timestamp('2024-01-01',tz='UTC'))];return finish(q)
def bars24(p):
 d=pd.read_csv(p);req={'time','bid_open','bid_high','bid_low','bid_close'};assert req<=set(d)
 q=pd.DataFrame({'time':pd.to_datetime(d.time,utc=True),'open':d.bid_open,'high':d.bid_high,'low':d.bid_low,'close':d.bid_close});q=q[(q.time>=pd.Timestamp('2024-01-01',tz='UTC'))&(q.time<pd.Timestamp('2025-01-01',tz='UTC'))];return finish(q)
def features(x):
 x=x.copy();pc=x.close.shift();tr=pd.concat([x.high-x.low,(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1);x['tr']=tr/PIP;x['body']=(x.close-x.open).abs()/PIP;x['dir']=np.sign(x.close-x.open);x['a16']=x.tr.rolling(16).mean();x['a20']=x.tr.rolling(20).mean();x['a96']=x.tr.rolling(96).mean();x['mtr']=x.tr.rolling(96).median();x['e20']=x.close.ewm(span=20,adjust=False).mean();x['e96']=x.close.ewm(span=96,adjust=False).mean();x['ts']=(x.e20-x.e96)/(x.a20*PIP);x['mu']=x.close.rolling(32).mean();sd=x.close.rolling(32).std(ddof=0);x['z']=(x.close-x.mu)/sd.replace(0,np.nan);x['hi16']=x.high.shift().rolling(16).max();x['lo16']=x.low.shift().rolling(16).min();x['hi32']=x.high.shift().rolling(32).max();x['lo32']=x.low.shift().rolling(32).min();path=x.close.diff().abs().rolling(32).sum()/PIP;x['eff']=(x.close-x.close.shift(32)).abs()/PIP/path.replace(0,np.nan);x['vr']=x.a20/x.a96;x['cr']=x.a16/x.a96
 pos=(x.close-x.low)/(x.high-x.low).replace(0,np.nan);x['shock']=(x.tr>=2.5*x.mtr)&(x.body>=.65*x.tr);x['sup']=x.shock&(x.dir>0)&(pos>=.8);x['sdn']=x.shock&(x.dir<0)&(pos<=.2);x['session']=pd.cut(x.hour,[-1,6,12,20,23],labels=['TOKYO','LONDON','NEW_YORK','ROLLOVER']).astype(str);x['vol']=np.select([x.vr<.75,x.vr>1.25],['LOW','HIGH'],default='NORMAL');x['state']=np.select([x.ts>=1,x.ts<=-1,x.eff<=.35],['UP_TREND','DOWN_TREND','BALANCE'],default='TRANSITION')
 day=x.groupby('date').agg(dh=('high','max'),dl=('low','min'));day['pdh']=day.dh.shift();day['pdl']=day.dl.shift();x=x.join(day[['pdh','pdl']],on='date');a=x[(x.hour>=0)&(x.hour<7)].groupby('date').agg(ah=('high','max'),al=('low','min'));x=x.join(a,on='date');o=x[x.hour==7].groupby('date').agg(oh=('high','max'),ol=('low','min'));return x.join(o,on='date')
def signals(x):
 fs=[]
 def add(m,v,s,r):
  idx=x.index[pd.Series(m,index=x.index).fillna(False).astype(bool)]
  if len(idx):fs.append(pd.DataFrame({'i':idx,'variant':v,'side':s,'reason':r}))
 rng=(x.high-x.low).replace(0,np.nan);br=(x.close-x.open).abs()/rng
 add((x.high>x.hi32)&(x.close<x.hi32)&(x.close<x.open),'A_FALSE_BREAKOUT_REVERSAL',-1,'upper_range_sweep');add((x.low<x.lo32)&(x.close>x.lo32)&(x.close>x.open),'A_FALSE_BREAKOUT_REVERSAL',1,'lower_range_sweep')
 bal=(x.ts.abs()<=.35)&(x.eff<=.35);add(bal&(x.z>=2),'B_BALANCE_MEAN_REVERSION',-1,'upper_two_sigma');add(bal&(x.z<=-2),'B_BALANCE_MEAN_REVERSION',1,'lower_two_sigma')
 add(x.sup,'C_SHOCK_CONTINUATION',1,'up_shock');add(x.sdn,'C_SHOCK_CONTINUATION',-1,'down_shock');mid=(x.high.shift()+x.low.shift())/2;add(x.sup.shift().astype('boolean').fillna(False)&(x.close<mid)&(x.close<x.open),'D_SHOCK_FAILURE',-1,'up_shock_failed');add(x.sdn.shift().astype('boolean').fillna(False)&(x.close>mid)&(x.close>x.open),'D_SHOCK_FAILURE',1,'down_shock_failed')
 for sh,eh,v in [(0,7,'E_TOKYO_LONDON'),(7,13,'E_LONDON_NY'),(13,21,'E_NY_TOKYO')]:
  g=x[(x.hour>=sh)&(x.hour<eh)].groupby('date').agg(op=('open','first'),cl=('close','last'),hi=('high','max'),lo=('low','min'),n=('time','size'));g['rg']=g.hi-g.lo;g['ef']=(g.cl-g.op).abs()/g.rg.replace(0,np.nan);g['ps']=(g.cl-g.lo)/g.rg.replace(0,np.nan);t=x[(x.hour==eh)&(x.minute==0)][['date']].join(g,on='date');ok=t.n>=max(8,(eh-sh)*3);m=pd.Series(False,index=x.index);m.loc[t.index]=ok&(t.ef>=.6)&(t.ps>=.8);add(m,v,1,'prior_session_close_high');m.loc[t.index]=ok&(t.ef>=.6)&(t.ps<=.2);add(m,v,-1,'prior_session_close_low')
 add(x.pdh.notna()&(x.high>x.pdh)&(x.close<x.pdh),'F_PREVIOUS_DAY_SWEEP',-1,'previous_day_high');add(x.pdl.notna()&(x.low<x.pdl)&(x.close>x.pdl),'F_PREVIOUS_DAY_SWEEP',1,'previous_day_low');aw=(x.hour>=7)&(x.hour<20);add(aw&x.ah.notna()&(x.high>x.ah)&(x.close<x.ah),'F_ASIAN_RANGE_SWEEP',-1,'asian_high');add(aw&x.al.notna()&(x.low<x.al)&(x.close>x.al),'F_ASIAN_RANGE_SWEEP',1,'asian_low')
 add((x.ts.shift()>=1.5)&(x.tr>=1.25*x.mtr)&(x.close<x.low.shift())&(x.close<x.open),'G_TREND_EXHAUSTION',-1,'uptrend_exhaustion');add((x.ts.shift()<=-1.5)&(x.tr>=1.25*x.mtr)&(x.close>x.high.shift())&(x.close>x.open),'G_TREND_EXHAUSTION',1,'downtrend_exhaustion')
 add((x.cr.shift()<=.6)&(x.close>x.hi16)&(x.close>x.open)&(br>=.5),'H_COMPRESSION_BREAKOUT',1,'upper_compression_break');add((x.cr.shift()<=.6)&(x.close<x.lo16)&(x.close<x.open)&(br>=.5),'H_COMPRESSION_BREAKOUT',-1,'lower_compression_break')
 add((x.ts.shift()>=1)&(x.high>x.hi16)&(x.close<x.e20)&(x.close<x.open),'I_FAILED_TREND_CONTINUATION',-1,'uptrend_failed');add((x.ts.shift()<=-1)&(x.low<x.lo16)&(x.close>x.e20)&(x.close>x.open),'I_FAILED_TREND_CONTINUATION',1,'downtrend_failed')
 tol=.25*x.a20*PIP;add((x.ts.shift()>=1)&(x.low<=x.e20+tol)&(x.close>x.e20)&(x.close>x.open),'J_PULLBACK_CONTINUATION',1,'uptrend_pullback');add((x.ts.shift()<=-1)&(x.high>=x.e20-tol)&(x.close<x.e20)&(x.close<x.open),'J_PULLBACK_CONTINUATION',-1,'downtrend_pullback')
 lw=(x.hour>=8)&(x.hour<=12);add(lw&x.oh.notna()&(x.close>x.oh)&(x.close>x.open),'K_LONDON_OPENING_RANGE_BREAKOUT',1,'london_or_up');add(lw&x.ol.notna()&(x.close<x.ol)&(x.close<x.open),'K_LONDON_OPENING_RANGE_BREAKOUT',-1,'london_or_down')
 up=np.ceil(x.close.shift()*2)/2;lo=np.floor(x.close.shift()*2)/2;uw=x.high-pd.concat([x.open,x.close],axis=1).max(axis=1);lwk=pd.concat([x.open,x.close],axis=1).min(axis=1)-x.low;add((x.high>=up)&(x.close<up)&(uw/rng>=.4),'K_ROUND_NUMBER_REJECTION',-1,'upper_half_yen');add((x.low<=lo)&(x.close>lo)&(lwk/rng>=.4),'K_ROUND_NUMBER_REJECTION',1,'lower_half_yen')
 mom=(x.close-x.close.shift(96))/PIP;dg=(x.hour==0)&(x.minute==0)&x.a96.notna();add(dg&(mom>=x.a96),'K_DAILY_TIME_SERIES_MOMENTUM',1,'four_day_up');add(dg&(mom<=-x.a96),'K_DAILY_TIME_SERIES_MOMENTUM',-1,'four_day_down')
 raw=pd.concat(fs,ignore_index=True).sort_values(['i','variant','side']).drop_duplicates(['i','variant','side']);raw['family_id']=raw.variant.map(V2F);raw['hold_bars']=raw.variant.map(HOLD);active={};seen=set();keep=[];daily={'F_PREVIOUS_DAY_SWEEP','F_ASIAN_RANGE_SWEEP','K_LONDON_OPENING_RANGE_BREAKOUT'}
 for r in raw.itertuples(index=False):
  i=int(r.i);h=int(r.hold_bars);key=(r.variant,x.date.iat[i],int(r.side))
  if i<100 or i+1+h>=len(x) or x.fold.iat[i]!=x.fold.iat[i+1+h] or i<=active.get(r.variant,-1) or (r.variant in daily and key in seen):continue
  active[r.variant]=i+h+1;seen.add(key);keep.append(r._asdict())
 return pd.DataFrame(keep)
def opportunities(s,x):
 rows=[]
 for r in s.itertuples(index=False):
  i=int(r.i);e=i+1;q=e+int(r.hold_bars);a=x.iloc[i];b=x.iloc[e];c=x.iloc[q];p=int(r.side)*(c.open-b.open)/PIP-COST;rows.append({'opportunity_id':f'{a.fold}|{r.variant}|{b.time.isoformat()}|{r.side}','family_id':r.family_id,'family':NAMES[r.family_id],'variant':r.variant,'reason':r.reason,'fold':a.fold,'signal_utc':a.time,'entry_utc':b.time,'exit_utc':c.time,'side':int(r.side),'side_label':'LONG' if r.side>0 else 'SHORT','hold_bars':int(r.hold_bars),'entry_bid':b.open,'exit_bid':c.open,'net_pips':p,'normalized_pl_jpy':p*JPYPP,'session':b.session,'volatility_state':b.vol,'market_state':b.state,'atr20_pips':b.a20,'vol_ratio':b.vr,'entry_date':b.time.strftime('%Y-%m-%d'),'entry_hour_utc':int(b.hour)})
 return pd.DataFrame(rows).sort_values(['entry_utc','variant','side']).reset_index(drop=True)
def baseline(p):
 t=pd.read_csv(p);req={'fold','strategy','entry_utc','close_utc','side','realized_pl_jpy'};assert req<=set(t);t.entry_utc=pd.to_datetime(t.entry_utc,utc=True);t.close_utc=pd.to_datetime(t.close_utc,utc=True);t['entry_date']=t.entry_utc.dt.strftime('%Y-%m-%d');t=t[t.fold.isin(FOLDS)];assert len(t)==1882 and t.entry_utc.dt.year.max()<2025;return t
def overlap(o,b):
 z=o.copy()
 for st in ['B02','F05']:
  q=b[b.strategy==st];near=[];sim=[]
  for r in z.itertuples(index=False):near.append(bool(len(q[(q.entry_utc>=r.entry_utc-pd.Timedelta('60min'))&(q.entry_utc<=r.entry_utc+pd.Timedelta('60min'))])));sim.append(bool(len(q[(q.entry_utc<r.exit_utc)&(q.close_utc>r.entry_utc)])))
  z[f'near_entry_{st}']=near;z[f'simultaneous_{st}']=sim
 z['simultaneous_any_baseline']=z.simultaneous_B02|z.simultaneous_F05;return z
def family_ledger(o):
 out=[]
 for _,g in o.groupby('family_id',sort=False):
  until=pd.Timestamp.min.tz_localize('UTC')
  for r in g.sort_values(['entry_utc','variant']).itertuples(index=False):
   if r.entry_utc<until:continue
   out.append(r._asdict());until=r.exit_utc
 return pd.DataFrame(out)
def days(b,c):
 idx=pd.Index(pd.date_range('2023-01-01','2024-12-31',tz='UTC').strftime('%Y-%m-%d'));ser=lambda d,col:d.groupby('entry_date')[col].sum().reindex(idx,fill_value=0.)
 return pd.DataFrame({'base':ser(b,'realized_pl_jpy'),'B02':ser(b[b.strategy=='B02'],'realized_pl_jpy'),'F05':ser(b[b.strategy=='F05'],'realized_pl_jpy'),'cand':ser(c,'normalized_pl_jpy')})
def mdd(s):
 e=s.fillna(0).cumsum();return float((e.cummax()-e).max()) if len(e) else 0.
def corr(a,b):return 0. if a.std(ddof=0)==0 or b.std(ddof=0)==0 or not np.isfinite(a.corr(b)) else float(a.corr(b))
def pf(s):
 gp=s[s>0].sum();gl=-s[s<0].sum();return None if gl==0 else float(gp/gl)
def rankscore(v):return pd.Series(50.,index=v.index) if v.max()==v.min() else 100*v.clip(lower=0).rank(pct=True)
def metrics(o,b,key):
 base=days(b,o.iloc[:0]);bm=mdd(base.base);bl=-base.loc[base.base<0,'base'].sum();bp=base.loc[base.base>0,'base'].sum();rows=[];fold=[];sess=[];state=[]
 for k,g in o.groupby(key,sort=False):
  f=g.family_id.iloc[0];d=days(b,g);comb=d.base+d.cand;weak=d.base<0;strong=d.base>0;fn=g.groupby('fold').normalized_pl_jpy.sum().reindex(FOLDS,fill_value=0);sn=g.groupby('side_label').normalized_pl_jpy.sum().reindex(['LONG','SHORT'],fill_value=0);ss=g.groupby('session').normalized_pl_jpy.sum();sc=g.groupby('session').size();valid=sc[sc>=5].index;sr=float((ss.reindex(valid,fill_value=0)>0).mean()) if len(valid) else 0.;cb=corr(d.cand,d.B02);cf=corr(d.cand,d.F05);ov=g.simultaneous_any_baseline.mean();ind=max(0,1-.5*((abs(cb)+abs(cf))/2)-.5*ov);net=g.normalized_pl_jpy.sum();weaknet=d.loc[weak,'cand'].sum();damage=-d.loc[strong,'cand'].clip(upper=0).sum();cov=d.loc[weak,'cand'].clip(lower=0).sum()/bl if bl else 0.;posf=int((fn>0).sum());poss=int((sn>0).sum());rob=.5*posf/4+.2*poss/2+.2*sr+(.1 if net>0 else 0)
  rows.append({key:k,'family_id':f,'family':NAMES[f],'opportunity_count':len(g),'annualized_opportunity_count':len(g)/2,'winner_count':int((g.normalized_pl_jpy>0).sum()),'loser_count':int((g.normalized_pl_jpy<=0).sum()),'win_rate':(g.normalized_pl_jpy>0).mean(),'expected_profit_contribution_jpy':net,'net_pips':g.net_pips.sum(),'profit_factor':pf(g.normalized_pl_jpy),'expected_coverage':cov,'weak_market_net_contribution_jpy':weaknet,'negative_day_loss_reduction_jpy':bl+comb[comb<0].sum(),'baseline_net_jpy':b.realized_pl_jpy.sum(),'theoretical_combined_net_jpy':b.realized_pl_jpy.sum()+net,'baseline_max_drawdown_jpy':bm,'theoretical_combined_max_drawdown_jpy':mdd(comb),'max_drawdown_improvement_jpy':bm-mdd(comb),'correlation_to_B02':cb,'correlation_to_F05':cf,'near_entry_overlap_B02':g.near_entry_B02.mean(),'near_entry_overlap_F05':g.near_entry_F05.mean(),'simultaneous_holding_rate_B02':g.simultaneous_B02.mean(),'simultaneous_holding_rate_F05':g.simultaneous_F05.mean(),'simultaneous_holding_rate_any':ov,'winner_damage_jpy':damage,'winner_damage_risk':damage/bp if bp else 0.,'portfolio_diversification':max(0,1-(abs(cb)+abs(cf))/2),'independence_raw':ind,'positive_folds':posf,'worst_fold_jpy':fn.min(),'best_fold_jpy':fn.max(),'fold_portability':posf/4,'positive_sides':poss,'long_short_symmetry':poss/2,'session_robustness':sr,'primary_session':ss.idxmax(),'primary_volatility_state':g.groupby('volatility_state').normalized_pl_jpy.sum().idxmax(),'primary_market_state':g.groupby('market_state').normalized_pl_jpy.sum().idxmax(),'practical_implementability':SIMPLE[f]/100,'data_authority':.85,'robustness_raw':min(1,max(0,rob))})
  for q in FOLDS:
   z=g[g.fold==q];fold.append({key:k,'family_id':f,'fold':q,'opportunities':len(z),'long_count':int((z.side>0).sum()),'short_count':int((z.side<0).sum()),'net_pips':z.net_pips.sum(),'normalized_pl_jpy':z.normalized_pl_jpy.sum(),'win_rate':(z.normalized_pl_jpy>0).mean() if len(z) else None})
  for q,z in g.groupby('session'):sess.append({key:k,'family_id':f,'session':q,'opportunities':len(z),'net_pips':z.net_pips.sum(),'normalized_pl_jpy':z.normalized_pl_jpy.sum(),'win_rate':(z.normalized_pl_jpy>0).mean()})
  for (q,v),z in g.groupby(['market_state','volatility_state']):state.append({key:k,'family_id':f,'market_state':q,'volatility_state':v,'opportunities':len(z),'net_pips':z.net_pips.sum(),'normalized_pl_jpy':z.normalized_pl_jpy.sum(),'win_rate':(z.normalized_pl_jpy>0).mean()})
 m=pd.DataFrame(rows);raw=m.expected_profit_contribution_jpy+m.weak_market_net_contribution_jpy+.5*m.max_drawdown_improvement_jpy-m.winner_damage_jpy;m['improvement_potential_score']=rankscore(raw);m['independence_score']=100*m.independence_raw;m['coverage_score']=100*m.expected_coverage.clip(0,1);m['robustness_score']=100*m.robustness_raw;m['simplicity_score']=m.family_id.map(SIMPLE);m['data_authority_score']=85.;m['economic_viability_factor']=np.select([(m.expected_profit_contribution_jpy>0)&(m.weak_market_net_contribution_jpy>0),(m.expected_profit_contribution_jpy>0)|(m.weak_market_net_contribution_jpy>0)],[1.,.75],default=.4);m['overall_score']=m.economic_viability_factor*(.3*m.improvement_potential_score+.2*m.independence_score+.15*m.coverage_score+.15*m.robustness_score+.1*m.simplicity_score+.1*m.data_authority_score);m=m.sort_values(['overall_score','expected_profit_contribution_jpy'],ascending=False).reset_index(drop=True);m.insert(0,'overall_rank',range(1,len(m)+1));return m,pd.DataFrame(fold),pd.DataFrame(sess),pd.DataFrame(state)
def complete(m,fold,b):
 miss=set(FAMS)-set(m.family_id)
 for f in sorted(miss):
  r={c:0. for c in m.columns if c not in ['family_id','family','primary_session','primary_volatility_state','primary_market_state','profit_factor']};r.update(family_id=f,family=NAMES[f],profit_factor=None,baseline_net_jpy=b.realized_pl_jpy.sum(),theoretical_combined_net_jpy=b.realized_pl_jpy.sum(),primary_session='NO_OPPORTUNITY',primary_volatility_state='NO_OPPORTUNITY',primary_market_state='NO_OPPORTUNITY',practical_implementability=SIMPLE[f]/100,data_authority=.85,simplicity_score=SIMPLE[f],data_authority_score=85,overall_score=0);m=pd.concat([m,pd.DataFrame([r])],ignore_index=True)
  fold=pd.concat([fold,pd.DataFrame([{'family_id':f,'fold':q,'opportunities':0,'long_count':0,'short_count':0,'net_pips':0.,'normalized_pl_jpy':0.,'win_rate':None} for q in FOLDS])],ignore_index=True)
 m=m.sort_values(['overall_score','expected_profit_contribution_jpy'],ascending=False).reset_index(drop=True);m['overall_rank']=range(1,len(m)+1);return m,fold
def clean(v):
 if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
 if isinstance(v,list):return [clean(x) for x in v]
 if isinstance(v,(np.integer,)):return int(v)
 if isinstance(v,(float,np.floating)):return None if not np.isfinite(v) else float(v)
 if isinstance(v,pd.Timestamp):return v.isoformat()
 return v
def report(out,fm,vm,pop,top3,rs,cs,run):
 L=['# USDJPY CSOS Opportunity Atlas v1','','`CSOS_OPPORTUNITY_ATLAS_COMPLETE_NO_EA_AUTHORIZATION`','',f'- Research SHA: `{rs}`',f'- Core SHA inspected: `{cs}`',f'- Run: `{run}`','- Periods: 2023H1, 2023H2, 2024H1, 2024H2','- 2025 accessed: false','- B02/F05 modified: false','- Optimization / EA / MT4 / Core modification: false','','## Opportunity Atlas','','|Rank|Family|Opp./yr|Net|Weak-market net|Coverage|Corr B02|Corr F05|Overlap|Positive folds|MDD improvement|Score|','|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in fm.itertuples():L.append(f'|{r.overall_rank}|{r.family_id} — {r.family}|{r.annualized_opportunity_count:.1f}|¥{r.expected_profit_contribution_jpy:,.0f}|¥{r.weak_market_net_contribution_jpy:,.0f}|{r.expected_coverage:.1%}|{r.correlation_to_B02:.3f}|{r.correlation_to_F05:.3f}|{r.simultaneous_holding_rate_any:.1%}|{int(r.positive_folds)}/4|¥{r.max_drawdown_improvement_jpy:,.0f}|{r.overall_score:.1f}|')
 L+=['','## Top 10 fixed variants','']+[f"{r.overall_rank}. **{r.variant}** — score {r.overall_score:.1f}; {r.opportunity_count} opportunities; ¥{r.expected_profit_contribution_jpy:,.0f}; {int(r.positive_folds)}/4 folds." for r in vm.head(10).itertuples()]+['','## Top 3 next-stage priorities','']+[f"{i}. **{r['family_id']} — {r['family']}** — {r['research_priority_status']}; score {r['overall_score']:.1f}; ¥{r['expected_profit_contribution_jpy']:,.0f}." for i,r in enumerate(top3,1)]+['','## Boundaries and limitations','','The top family is a research priority, not an adopted third strategy. Portfolio values are additive fixed-lot estimates without margin, variable spread, slippage, or admission conflicts. 2024 accepted Bid/Ask-derived bars are not Rakuten quote history. Carry, value, order-flow, macro-surprise and options families remain unquantified because authoritative inputs are absent.']
 (out/'opportunity_atlas_report.md').write_text('\n'.join(L)+'\n')
def main():
 a=argparse.ArgumentParser();a.add_argument('--m15-2023',type=Path,required=True);a.add_argument('--m15-2024',type=Path,required=True);a.add_argument('--baseline-trades',type=Path,required=True);a.add_argument('--family-catalog',type=Path,required=True);a.add_argument('--prereg',type=Path,required=True);a.add_argument('--literature',type=Path,required=True);a.add_argument('--out-dir',type=Path,required=True);a.add_argument('--research-sha',default='UNKNOWN');a.add_argument('--core-sha',default='UNKNOWN');a.add_argument('--run-id',default='LOCAL');z=a.parse_args();z.out_dir.mkdir(parents=True,exist_ok=True);pre=json.load(open(z.prereg));assert pre['development_folds']==FOLDS and set(pre['forbidden_periods'])=={'2025H1','2025H2'} and pre['selection_boundary']['parameter_optimization'] is False
 b23=bars23(z.m15_2023);b24=bars24(z.m15_2024);x=features(pd.concat([b23,b24],ignore_index=True).sort_values('time').reset_index(drop=True));assert set(x.fold)==set(FOLDS) and x.time.dt.year.max()<2025;o=opportunities(signals(x),x);assert len(o);b=baseline(z.baseline_trades);o=overlap(o,b);fo=overlap(family_ledger(o),b);fm,ff,fs,fst=metrics(fo,b,'family_id');vm,vf,vs,vst=metrics(o,b,'variant');fm,ff=complete(fm,ff,b)
 for p,d in [('strategy_opportunity_atlas.csv.gz',o),('family_nonoverlap_opportunity_ledger.csv.gz',fo)]:d.to_csv(z.out_dir/p,index=False,compression='gzip')
 for p,d in [('family_comparison.csv',fm),('variant_comparison.csv',vm),('family_fold_metrics.csv',ff),('variant_fold_metrics.csv',vf),('family_session_metrics.csv',fs),('variant_session_metrics.csv',vs),('family_market_state_metrics.csv',fst),('variant_market_state_metrics.csv',vst)]:d.to_csv(z.out_dir/p,index=False)
 cols=['family_id','family','correlation_to_B02','correlation_to_F05','near_entry_overlap_B02','near_entry_overlap_F05','simultaneous_holding_rate_B02','simultaneous_holding_rate_F05','simultaneous_holding_rate_any','portfolio_diversification','independence_score'];fm[cols].to_csv(z.out_dir/'family_overlap_correlation.csv',index=False)
 imp=fm.sort_values(['expected_profit_contribution_jpy','negative_day_loss_reduction_jpy','max_drawdown_improvement_jpy'],ascending=False).reset_index(drop=True);imp.insert(0,'improvement_rank',range(1,len(imp)+1));imp.to_csv(z.out_dir/'expected_improvement_ranking.csv',index=False);co=fm.sort_values(['independence_score','portfolio_diversification','expected_coverage'],ascending=False).reset_index(drop=True);co.insert(0,'complementarity_rank',range(1,len(co)+1));co.to_csv(z.out_dir/'complementarity_ranking.csv',index=False)
 top10=clean(vm.head(10).to_dict('records'));sel=[];used=set()
 for d,status in [(fm[(fm.expected_profit_contribution_jpy>0)&(fm.positive_folds>=3)],'PORTABLE_POSITIVE_PRIORITY'),(fm[fm.expected_profit_contribution_jpy>0],'POSITIVE_BUT_PORTABILITY_LIMITED'),(fm,'EXPLORATORY_RANK_ONLY')]:
  for r in d.to_dict('records'):
   if r['family_id'] in used:continue
   r['research_priority_status']=status;sel.append(r);used.add(r['family_id'])
   if len(sel)==3:break
  if len(sel)==3:break
 top3=clean(sel);(z.out_dir/'top10_candidates.json').write_text(json.dumps(top10,indent=2,ensure_ascii=False)+'\n');(z.out_dir/'top3_research_priorities.json').write_text(json.dumps(top3,indent=2,ensure_ascii=False)+'\n');pop={'bars_2023':len(b23),'bars_2024':len(b24),'baseline_trades':len(b),'variant_opportunities':len(o),'family_opportunities':len(fo),'family_count':fm.family_id.nunique(),'variant_count':vm.variant.nunique()};report(z.out_dir,fm,vm,pop,top3,z.research_sha,z.core_sha,z.run_id)
 sources={k:{'path':str(p),'sha256':sha(p)} for k,p in {'m15_2023':z.m15_2023,'m15_2024':z.m15_2024,'baseline_trades':z.baseline_trades,'family_catalog':z.family_catalog,'prereg':z.prereg,'literature':z.literature}.items()};receipt=clean({'schema_version':'usdjpy_csos_opportunity_atlas_execution_receipt_v1','status':'CSOS_OPPORTUNITY_ATLAS_COMPLETE_NO_EA_AUTHORIZATION','research_sha':z.research_sha,'core_sha_inspected':z.core_sha,'run_id':z.run_id,'periods':FOLDS,'excluded_periods':['2025H1','2025H2'],'population':pop,'sources':sources,'top_family':fm.iloc[0].to_dict(),'top10_variants':top10,'top3_research_priorities':top3,'boundaries':{'2025_accessed':False,'B02_F05_logic_changed':False,'parameter_optimization':False,'EA_implemented':False,'MT4_accessed':False,'Core_modified':False,'production_authorized':False},'portfolio_estimate':'ADDITIVE_UNCONSTRAINED_RESEARCH_ESTIMATE'});(z.out_dir/'execution_receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False,sort_keys=True)+'\n');(z.out_dir/'limitations.json').write_text(json.dumps({'cross_venue_2024':'accepted public Bid/Ask-derived bars; not Rakuten history','fixed_horizon':True,'unquantified':['carry','value','order flow','macro surprise','options'],'2025_accessed':False},indent=2)+'\n')
 for p in [z.family_catalog,z.prereg,z.literature]:(z.out_dir/p.name).write_bytes(p.read_bytes())
 files=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(z.out_dir.iterdir()) if p.is_file() and p.name!='artifact_manifest.json'];(z.out_dir/'artifact_manifest.json').write_text(json.dumps({'schema_version':'usdjpy_csos_opportunity_atlas_manifest_v1','files':files,'2025_accessed':False,'ea_implementation':False},indent=2,sort_keys=True)+'\n');print(json.dumps({'status':receipt['status'],'top_family':receipt['top_family']['family_id'],'top_family_name':receipt['top_family']['family'],'family_count':pop['family_count'],'variant_count':pop['variant_count'],'variant_opportunities':pop['variant_opportunities'],'2025_accessed':False},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())

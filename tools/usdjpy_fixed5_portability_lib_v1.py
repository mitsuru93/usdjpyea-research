from __future__ import annotations
import json, hashlib, math
from pathlib import Path
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd
PIP=0.01
IDS=['R1B02_legacy_asia_00_07_breakout','R1E02_legacy_trend_8h_resumption','R1E03_trend_12h_resumption','R1F05_donchian_96','R1H04_ramom_32_64_z125']
META={'id','origin','legacy_ids','h2_information_status','literature_refs','family'}
def canon_json(x): return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def sha(x): return hashlib.sha256(x).hexdigest()
def norm_def(c): return {'family':c['family'],'parameters':{k:v for k,v in c.items() if k not in META}}
def nth_sunday(y,m,n,h):
 d=datetime(y,m,1,h,tzinfo=timezone.utc); return pd.Timestamp(d+timedelta(days=(6-d.weekday())%7+7*(n-1)))
def us_dst(ts):
 return ts>=nth_sunday(ts.year,3,2,7) and ts<nth_sunday(ts.year,11,1,6)
def server_to_hist_utc(s):
 wc=s-pd.Timedelta(hours=2)
 return s-pd.Timedelta(hours=3) if us_dst(wc) else wc
def load23(p):
 d=pd.read_csv(p)
 true=pd.to_datetime(d.timestamp_utc,utc=True)
 server=pd.to_datetime(d.first_timestamp_mt4_server,utc=True)
 hist=pd.DatetimeIndex([server_to_hist_utc(x) for x in server])
 print('shifted',int((hist!=true).sum()),'dups',hist.duplicated().sum(),'mono',hist.is_monotonic_increasing)
 out=pd.DataFrame({'timestamp_utc':hist,'symbol':'USDJPY','mid_open':d.open,'mid_high':d.high,'mid_low':d.low,'mid_close':d.close,'spread_open_pips':0.5,'spread_mean_pips':0.5})
 return enrich(out)
def load24(p):
 d=pd.read_csv(p,compression='gzip')
 cols=['timestamp_utc','symbol','mid_open','mid_high','mid_low','mid_close','spread_open_pips','spread_mean_pips']
 return enrich(d[cols].copy())
def enrich(d):
 d=d.copy(); d.timestamp_utc=pd.to_datetime(d.timestamp_utc,utc=True); d=d.sort_values('timestamp_utc').reset_index(drop=True)
 d['date_utc']=d.timestamp_utc.dt.strftime('%Y-%m-%d'); d['month_utc']=d.timestamp_utc.dt.strftime('%Y-%m'); d['hour_utc']=d.timestamp_utc.dt.hour.astype(int); d['minute_utc']=d.timestamp_utc.dt.minute.astype(int)
 pc=d.mid_close.shift(1); d['true_range']=pd.concat([(d.mid_high-d.mid_low),(d.mid_high-pc).abs(),(d.mid_low-pc).abs()],axis=1).max(axis=1); d['bar_body']=d.mid_close-d.mid_open
 return d
def allowed_hours(b,c):
 if 'entry_hours_utc' in c:
  entry=b.timestamp_utc.shift(-1); return entry.dt.hour.isin([int(x) for x in c['entry_hours_utc']])
 if 'entry_start_hour' in c: return (b.hour_utc>=int(c['entry_start_hour']))&(b.hour_utc<=int(c['entry_end_hour_inclusive']))
 return pd.Series(True,index=b.index)
def first_dir_day(side,b):
 keep=pd.Series(0,index=side.index,dtype='int8'); s=pd.DataFrame({'side':side,'date':b.date_utc,'ts':b.timestamp_utc}); s=s[s.side.isin([1,-1])]
 if len(s):
  idx=s.sort_values('ts').groupby(['date','side'],sort=False).head(1).index; keep.loc[idx]=side.loc[idx].astype('int8')
 return keep
def session_ref(b,a,z):
 ref=b[(b.hour_utc>=a)&(b.hour_utc<z)]; daily=ref.groupby('date_utc').agg(ref_open=('mid_open','first'),ref_high=('mid_high','max'),ref_low=('mid_low','min'),ref_close=('mid_close','last')); return b[['date_utc']].join(daily,on='date_utc')
def signal(b,c):
 fam=c['family']; allow=allowed_hours(b,c); s=pd.Series(0,index=b.index,dtype='int8')
 if fam=='session_range_breakout':
  r=session_ref(b,int(c['reference_start_hour']),int(c['reference_end_hour_exclusive'])); s.loc[allow&(b.mid_close>r.ref_high)]=1; s.loc[allow&(b.mid_close<r.ref_low)]=-1; s=first_dir_day(s,b)
 elif fam=='trend_pullback_resumption':
  n=int(c['trend_bars']); tr=b.mid_close.shift(1)-b.mid_open.shift(n); pb=b.mid_close.shift(1)<b.mid_open.shift(1); pu=b.mid_close.shift(1)>b.mid_open.shift(1); s.loc[allow&(tr>0)&pb&(b.mid_close>b.mid_high.shift(1))]=1; s.loc[allow&(tr<0)&pu&(b.mid_close<b.mid_low.shift(1))]=-1
 elif fam=='donchian_channel_breakout':
  n=int(c['lookback_bars']); hi=b.mid_high.shift(1).rolling(n,min_periods=n).max(); lo=b.mid_low.shift(1).rolling(n,min_periods=n).min(); s.loc[allow&(b.mid_close>hi)&(b.mid_close.shift(1)<=hi.shift(1))]=1; s.loc[allow&(b.mid_close<lo)&(b.mid_close.shift(1)>=lo.shift(1))]=-1
 elif fam=='volatility_adjusted_momentum':
  lb=int(c['lookback_bars']); vw=int(c['volatility_window_bars']); th=float(c['score_threshold']); cum=(b.mid_close-b.mid_close.shift(lb))/PIP; one=b.mid_close.diff()/PIP; rv=np.sqrt(one.pow(2).rolling(vw,min_periods=vw).sum()); sc=cum/rv.replace(0,np.nan); s.loc[allow&(sc>th)&(sc.shift(1)<=th)]=1; s.loc[allow&(sc<-th)&(sc.shift(1)>=-th)]=-1
 else: raise ValueError(fam)
 return s
def hard_excl(entry):
 local=entry.dt.tz_convert(ZoneInfo('America/New_York')).dt.time
 return (local>=time(16,0))&(local<time(19,0))
def build_signals(b,c,start,end):
 raw=signal(b,c); w=pd.DataFrame({'signal_dt':b.timestamp_utc,'entry_dt':b.timestamp_utc.shift(-1),'side':raw}); w=w[w.side.isin([1,-1])&w.entry_dt.notna()].copy(); w=w[(w.entry_dt>=start)&(w.entry_dt<end)]; w=w[~hard_excl(w.entry_dt)].copy(); w['candidate_id']=c['id']; w['family']=c['family']; w['definition_sha256']=sha(canon_json(norm_def(c))); w['signal_ts']=w.signal_dt.dt.strftime('%Y-%m-%dT%H:%M:%SZ'); w['entry_ts']=w.entry_dt.dt.strftime('%Y-%m-%dT%H:%M:%SZ'); w['signal_month']=w.signal_dt.dt.strftime('%Y-%m'); w['signal_hour_utc']=w.signal_dt.dt.hour.astype(int); w['entry_month']=w.entry_dt.dt.strftime('%Y-%m'); w['entry_hour_utc']=w.entry_dt.dt.hour.astype(int)
 return w[['candidate_id','family','definition_sha256','signal_ts','entry_ts','side','signal_month','signal_hour_utc','entry_month','entry_hour_utc']].sort_values(['candidate_id','signal_ts','side']).reset_index(drop=True)
def build_trades(b,sigs,specs,start,end):
 mp=pd.Series(b.index.to_numpy(),index=b.timestamp_utc).to_dict(); opens=b.mid_open.to_numpy(float); closes=b.mid_close.to_numpy(float); spreads=b.spread_mean_pips.to_numpy(float); ts=b.timestamp_utc.tolist(); months=b.month_utc.to_numpy(str); dates=b.date_utc.to_numpy(str); by={x['candidate_id']:x for x in specs}; frames=[]
 for cid,g in sigs.groupby('candidate_id',sort=False):
  sp=by[cid]; h=int(sp['time_cap_bars']); w=g.copy(); w['entry_dt']=pd.to_datetime(w.entry_ts,utc=True); w['entry_index']=w.entry_dt.map(mp); assert w.entry_index.notna().all(),cid; ei=w.entry_index.astype(int).to_numpy(); xi=ei+h-1; valid=xi<len(b); xc=np.minimum(xi,len(b)-1); valid &= np.array([ts[i]<end for i in xc]); valid &= np.array([ts[i]>=start for i in ei]); valid &= months[ei]==months[xc]; pos=np.where(valid)[0]
  if not len(pos): continue
  ei=ei[pos]; xi=xi[pos]; sel=w.iloc[pos].reset_index(drop=True); sides=sel.side.astype(int).to_numpy(); gross=sides*(closes[xi]-opens[ei])/PIP; cost=np.maximum(0.5,spreads[ei]); sev=cost*3+1
  f=pd.DataFrame({'freeze_rank':int(sp['freeze_rank']),'strategy_id':sp['strategy_id'],'candidate_id':cid,'family':sp['family'],'definition_sha256':sp['entry_definition_sha256'],'time_cap_bars':h,'policy_id':'T0_fixed_time_cap','mechanism':'fixed_time','signal_ts':sel.signal_ts,'entry_ts':sel.entry_ts,'exit_ts':[ts[i].strftime('%Y-%m-%dT%H:%M:%SZ') for i in xi],'entry_month':months[ei],'entry_date_utc':dates[ei],'side':sides,'entry_mid':opens[ei],'exit_mid':closes[xi],'entry_spread_pips':spreads[ei],'bars_held':h,'gross_pips':gross,'default_cost_pips':cost,'severe_cost_pips':sev,'default_net_pips':gross-cost,'severe_net_pips':gross-sev})
  frames.append(f)
 return pd.concat(frames,ignore_index=True).sort_values(['freeze_rank','entry_ts','side']).reset_index(drop=True)

def historical_ledger(b,cs,start,end):
 frames=[]
 for cid,code,cap in [(IDS[0],'B02',48),(IDS[3],'F05',32)]:
  s=build_signals(b,cs[cid],start,end).copy(); s['strategy']=code; s['cap_bars']=cap
  if code=='B02':
   counts=b[(b.hour_utc>=0)&(b.hour_utc<7)].groupby('date_utc').size(); dates=pd.to_datetime(s.signal_ts,utc=True).dt.strftime('%Y-%m-%d'); s=s[dates.map(counts).fillna(0).to_numpy()>=28].copy()
  frames.append(s)
 s=pd.concat(frames).sort_values(['entry_ts','strategy']).reset_index(drop=True); mp=pd.Series(b.index,index=b.timestamp_utc).to_dict(); rows=[]
 for n,r in enumerate(s.itertuples(index=False),1):
  ei=int(mp[pd.Timestamp(r.entry_ts)]); xi=ei+int(r.cap_bars); side=int(r.side); eb=float(b.mid_open.iloc[ei]); ep=eb+(0.005 if side==1 else 0); closed=xi<len(b) and b.timestamp_utc.iloc[xi]<end
  if closed:
   cb=float(b.mid_open.iloc[xi]); cp=cb+(0 if side==1 else 0.005); gp=side*(cp-ep)/PIP; pl=float(round(gp*10)); cu=b.timestamp_utc.iloc[xi].strftime('%Y-%m-%dT%H:%M:%SZ')
  else: cb=cp=gp=pl=np.nan; cu=''
  rows.append({'trade_ordinal':n,'trade_key':f'{r.strategy}|{r.signal_ts}|{side}','strategy':r.strategy,'signal_utc':r.signal_ts,'entry_utc':r.entry_ts,'side':side,'entry_index':ei,'entry_bid':eb,'entry_price':ep,'cap_bars':int(r.cap_bars),'closed':closed,'close_index':xi,'close_utc':cu,'close_bid':cb,'close_price':cp,'gross_pips':gp,'realized_pl_jpy':pl})
 return pd.DataFrame(rows)

def profit_factor(v):
 gain=float(v[v>0].sum()); loss=float(-v[v<0].sum()); return (math.inf if gain>0 else 0.0) if loss==0 else gain/loss

def metrics(g,col):
 v=g[col].astype(float); m=g.groupby('entry_month')[col].sum() if len(g) else pd.Series(dtype=float); d=g.groupby('entry_date_utc')[col].sum() if len(g) else pd.Series(dtype=float); pos=d[d>0].sort_values(ascending=False); ps=float(pos.sum())
 return {'trades':int(len(g)),'net_pips':float(v.sum()),'pf':float(profit_factor(v)),'positive_months':int((m>0).sum()),'negative_months':int((m<0).sum()),'ex_best_two_dates':float(v.sum()-d.sort_values(ascending=False).head(2).sum()),'top_two_positive_date_share':0.0 if ps==0 else float(pos.head(2).sum()/ps)}

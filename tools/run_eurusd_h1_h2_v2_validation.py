#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

PIP=0.0001
ONE_HOUR=pd.Timedelta(hours=1)

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def dump(p:Path,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')

def load_bars(p:Path)->pd.DataFrame:
    d=pd.read_csv(p)
    req={'timestamp_utc','symbol','mid_open','mid_high','mid_low','mid_close','spread_mean_pips','tick_count'}
    miss=req-set(d.columns)
    if miss: raise ValueError(f'missing columns: {sorted(miss)}')
    d=d[list(req)].copy(); d['timestamp_utc']=pd.to_datetime(d.timestamp_utc,utc=True,errors='raise')
    for c in ['mid_open','mid_high','mid_low','mid_close','spread_mean_pips','tick_count']: d[c]=pd.to_numeric(d[c],errors='raise')
    d=d.sort_values('timestamp_utc').reset_index(drop=True)
    if d.timestamp_utc.duplicated().any(): raise ValueError('duplicate timestamps')
    if set(d.symbol.astype(str).str.upper())!={'EURUSD'}: raise ValueError('unexpected symbol')
    d['date_utc']=d.timestamp_utc.dt.strftime('%Y-%m-%d'); d['month']=d.timestamp_utc.dt.strftime('%Y-%m')
    return indicators(d)

def er(c,n):
    return (c-c.shift(n)).abs()/c.diff().abs().rolling(n,min_periods=n).sum().replace(0,np.nan)

def rsi(c,n):
    x=c.diff(); g=x.clip(lower=0); l=-x.clip(upper=0)
    ag=g.ewm(alpha=1/n,adjust=False,min_periods=n).mean(); al=l.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    out=100-100/(1+ag/al.replace(0,np.nan))
    return out.mask((al==0)&(ag>0),100).mask((al==0)&(ag==0),50)

def indicators(d):
    c=d.mid_close; m=c.rolling(72,min_periods=72).mean(); s=c.rolling(72,min_periods=72).std(ddof=0).replace(0,np.nan)
    d['z72']=(c-m)/s; d['er24']=er(c,24); d['rsi14']=rsi(c,14)
    pc=c.shift(1); tr=pd.concat([d.mid_high-d.mid_low,(d.mid_high-pc).abs(),(d.mid_low-pc).abs()],axis=1).max(axis=1)
    d['atr24']=tr.rolling(24,min_periods=24).mean()
    for lb in (24,48):
        d[f'ref_high_{lb}']=d.mid_high.shift(1).rolling(lb,min_periods=lb).max()
        d[f'ref_low_{lb}']=d.mid_low.shift(1).rolling(lb,min_periods=lb).min()
    return d

def specs(cfg): return cfg['diagnostic_baselines']+cfg['v2_candidates']

def hard_excluded(ts):
    x=ts.tz_convert(ZoneInfo('America/New_York'))
    return 16<=x.hour<19

def signal(d,s,cfg):
    side=pd.Series(0,index=d.index,dtype=int); meta={}; k=s['kind']; const=cfg['implementation_constants']
    if k=='A':
        entry=d.timestamp_utc.shift(-1).dt.tz_convert(ZoneInfo(const['A_timezone']))
        side.loc[entry.dt.hour.eq(int(const['A_entry_local_hour']))]=-1
    elif k=='F':
        reg=d.er24<=float(const['F_efficiency_ratio_maximum']); z=d.z72; th=float(s['entry_abs_z'])
        lc=(d.rsi14<float(const['F_rsi_thresholds'][0])) if s['rsi_confirmation'] else pd.Series(True,index=d.index)
        sc=(d.rsi14>float(const['F_rsi_thresholds'][1])) if s['rsi_confirmation'] else pd.Series(True,index=d.index)
        side.loc[reg&(z<=-th)&lc]=1; side.loc[reg&(z>=th)&sc]=-1
    elif k=='H_single':
        lb=int(s['reference_lookback_bars']); hi=d[f'ref_high_{lb}']; lo=d[f'ref_low_{lb}']; me=float(const['H_minimum_excursion_atr_fraction'])*d.atr24
        fh=(d.mid_high>hi)&(d.mid_close<=hi)&(d.mid_close>=lo)&((d.mid_high-hi)>=me)
        fl=(d.mid_low<lo)&(d.mid_close>=lo)&(d.mid_close<=hi)&((lo-d.mid_low)>=me)
        side.loc[fh&~fl]=-1; side.loc[fl&~fh]=1; meta['lookback']=pd.Series(lb,index=d.index)
    elif k=='H_hier':
        ss={}; frac=float(s['reentry_fraction'])
        for lb in (48,24):
            hi=d[f'ref_high_{lb}']; lo=d[f'ref_low_{lb}']; width=hi-lo; me=float(const['H_minimum_excursion_atr_fraction'])*d.atr24
            fh=(d.mid_high>hi)&(d.mid_close<=hi-frac*width)&(d.mid_close>=lo)&((d.mid_high-hi)>=me)
            fl=(d.mid_low<lo)&(d.mid_close>=lo+frac*width)&(d.mid_close<=hi)&((lo-d.mid_low)>=me)
            q=pd.Series(0,index=d.index,dtype=int); q.loc[fh&~fl]=-1; q.loc[fl&~fh]=1; ss[lb]=q
        u48=ss[48].isin([1,-1]); u24=(~u48)&ss[24].isin([1,-1])
        side.loc[u48]=ss[48].loc[u48]; side.loc[u24]=ss[24].loc[u24]
        lbv=pd.Series(np.nan,index=d.index); lbv.loc[u48]=48; lbv.loc[u24]=24; meta['lookback']=lbv
    else: raise ValueError(k)
    return side,meta

def trades(d,s,cfg,start,end):
    side,meta=signal(d,s,cfg); out=[]; last_exit=-1; cost=cfg['execution']
    for sig in side[side.isin([1,-1])].index:
        ent=int(sig)+1
        if ent>=len(d) or ent<=last_exit: continue
        ets=d.at[ent,'timestamp_utc']
        if not(start<=ets<end) or hard_excluded(ets): continue
        direction=int(side.at[sig]); ep=float(d.at[ent,'mid_open']); ex=None; reason='time'
        if s['kind']=='A':
            mh=int(s['maximum_hold_bars']); cp=s['checkpoint_bars']
            if cp is not None:
                i=int(sig)+int(cp)
                if i<len(d) and direction*(float(d.at[i,'mid_close'])-ep)/PIP<=float(s['weak_threshold_pips']): ex=i; reason=f'checkpoint_{cp}'
        elif s['kind']=='F':
            mh=int(s['maximum_hold_bars']); target=s['exit_target_abs_z']
            if target is not None:
                for h in range(1,mh+1):
                    i=int(sig)+h
                    if i>=len(d): break
                    z=d.at[i,'z72']
                    if pd.notna(z) and ((direction==1 and z>=-float(target)) or (direction==-1 and z<=float(target))): ex=i; reason=f'z_target_{target}'; break
        elif s['kind']=='H_single': mh=int(s['hold_bars'])
        else:
            lb=int(meta['lookback'].at[sig]); mh=12 if lb==48 else 6
            if s['midpoint_exit']:
                mid=(float(d.at[sig,f'ref_high_{lb}'])+float(d.at[sig,f'ref_low_{lb}']))/2
                for h in range(1,mh+1):
                    i=int(sig)+h
                    if i>=len(d): break
                    cl=float(d.at[i,'mid_close'])
                    if (direction==-1 and cl<=mid) or (direction==1 and cl>=mid): ex=i; reason='range_midpoint'; break
        if ex is None: ex=int(sig)+mh
        if ex>=len(d): continue
        xt=d.at[ex,'timestamp_utc']+ONE_HOUR
        if xt>end: continue
        xp=float(d.at[ex,'mid_close']); gross=direction*(xp-ep)/PIP
        spread=max(float(cost['base_spread_pips']),float(d.at[ent,'spread_mean_pips']))
        row={'candidate_id':s['id'],'family':s['family'],'signal_ts':d.at[sig,'timestamp_utc'],'entry_ts':ets,'exit_time_utc':xt,'side':direction,'hold_bars':ex-int(sig),'exit_reason':reason,'entry_mid':ep,'exit_mid':xp,'gross_pips':gross,'spread_basis_pips':spread,'net_pips':gross-spread,'severe_net_pips':gross-(spread*3+1.0),'entry_date_utc':ets.strftime('%Y-%m-%d'),'entry_month':ets.strftime('%Y-%m')}
        if 'lookback' in meta and pd.notna(meta['lookback'].at[sig]): row['lookback']=int(meta['lookback'].at[sig])
        out.append(row); last_exit=ex
    return pd.DataFrame(out)

def pf(x):
    g=float(x[x>0].sum()); l=float(-x[x<0].sum())
    return g/l if l else (math.inf if g else 0.0)

def summarize(t,months):
    if t.empty: return {'trades':0,'avg_net_pips':0.0,'total_net_pips':0.0,'profit_factor':0.0,'positive_months':0,'total_excluding_best_two_days':0.0,'severe_profit_factor':0.0,'max_drawdown_pips':0.0}
    mon=t.groupby('entry_month').net_pips.mean().reindex(months,fill_value=0); daily=t.groupby('entry_date_utc').net_pips.sum().sort_values(ascending=False)
    eq=t.sort_values('entry_ts').net_pips.cumsum(); dd=eq-eq.cummax()
    return {'trades':int(len(t)),'avg_net_pips':float(t.net_pips.mean()),'total_net_pips':float(t.net_pips.sum()),'profit_factor':pf(t.net_pips),'positive_months':int((mon>0).sum()),'total_excluding_best_two_days':float(t.net_pips.sum()-daily.head(2).sum()),'severe_profit_factor':pf(t.severe_net_pips),'max_drawdown_pips':float(dd.min())}

def pass_gate(x,g,full=False):
    ok=x['profit_factor']>=float(g['profit_factor_gte']) and x['positive_months']>=int(g['positive_months_gte']) and x['trades']>=int(g['trades_gte'])
    if 'avg_net_pips_gt' in g: ok=ok and x['avg_net_pips']>float(g['avg_net_pips_gt'])
    if full or 'total_excluding_best_two_days_gt' in g: ok=ok and x['total_excluding_best_two_days']>float(g['total_excluding_best_two_days_gt']) and x['severe_profit_factor']>=float(g['severe_profit_factor_gte'])
    return bool(ok)

def frame_hash(d):
    w=d[['timestamp_utc','symbol','mid_open','mid_high','mid_low','mid_close','spread_mean_pips','tick_count']].copy(); w.timestamp_utc=w.timestamp_utc.dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    return hashlib.sha256(w.to_csv(index=False,float_format='%.15g',lineterminator='\n').encode()).hexdigest()

def development(args,cfg,d):
    start=pd.Timestamp(cfg['period_policy']['development_start_utc']); end=pd.Timestamp(cfg['period_policy']['development_end_utc_exclusive'])
    if d.timestamp_utc.max()>=end: raise ValueError('development input contains H2')
    rows=[]; tt=[]
    for s in specs(cfg):
        t=trades(d,s,cfg,start,end); m=summarize(t,[f'2024-{i:02d}' for i in range(1,7)]); m.update(candidate_id=s['id'],family=s['family'],kind=s['kind'],is_v2=s in cfg['v2_candidates'])
        m['development_pass']=pass_gate(m,cfg['development_gate'],full=True); rows.append(m)
        if not t.empty: tt.append(t)
    summary=pd.DataFrame(rows); out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    summary.to_csv(out/'development_summary.csv',index=False); pd.concat(tt,ignore_index=True).to_csv(out/'development_trades.csv',index=False)
    locked=[s for s in cfg['v2_candidates'] if bool(summary.loc[summary.candidate_id==s['id'],'development_pass'].iloc[0])]
    payload={'version':'v2','created_by':'development_phase','development_period':{'start_utc':str(start),'end_utc_exclusive':str(end)},'candidate_ids':[s['id'] for s in locked],'candidate_definitions':locked,'protocol_sha256':sha256_file(args.protocol),'development_frame_content_sha256':frame_hash(d),'rule':'2024 H1 only; definitions frozen before reusable fixed 2024 H2 validation.'}
    raw=json.dumps(payload,sort_keys=True,separators=(',',':')).encode(); payload['candidate_lock_sha256']=hashlib.sha256(raw).hexdigest(); dump(out/'development_lock.json',payload)
    print(summary.to_string(index=False)); print(json.dumps(payload,indent=2))

def validation(args,cfg,d):
    lock=json.loads(args.development_lock.read_text()); defs=lock['candidate_definitions']; start=pd.Timestamp(cfg['period_policy']['fixed_validation_start_utc']); end=pd.Timestamp(cfg['period_policy']['fixed_validation_end_utc_exclusive']); ds=pd.Timestamp(cfg['period_policy']['development_start_utc']); de=pd.Timestamp(cfg['period_policy']['development_end_utc_exclusive'])
    rows=[]; all_t=[]
    for s in defs:
        td=trades(d,s,cfg,ds,de); tv=trades(d,s,cfg,start,end); full=pd.concat([td,tv],ignore_index=True)
        md=summarize(td,[f'2024-{i:02d}' for i in range(1,7)]); mv=summarize(tv,[f'2024-{i:02d}' for i in range(7,13)]); mf=summarize(full,[f'2024-{i:02d}' for i in range(1,13)])
        r={'candidate_id':s['id'],'family':s['family'],**{f'h1_{k}':v for k,v in md.items()},**{f'h2_{k}':v for k,v in mv.items()},**{f'full_{k}':v for k,v in mf.items()}}
        r['h2_pass']=pass_gate(mv,cfg['validation_gate']); r['full_pass']=pass_gate(mf,cfg['full_year_gate'],full=True); r['final_pass']=r['h2_pass'] and r['full_pass']; rows.append(r)
        if not tv.empty: all_t.append(tv.assign(period='H2'))
    out=args.output_dir; out.mkdir(parents=True,exist_ok=True); res=pd.DataFrame(rows).sort_values(['final_pass','h2_profit_factor'],ascending=[False,False]); res.to_csv(out/'validation_summary.csv',index=False)
    if all_t: pd.concat(all_t,ignore_index=True).to_csv(out/'validation_trades.csv',index=False)
    final=res.loc[res.final_pass,'candidate_id'].tolist(); payload={'version':'v2','candidate_lock_sha256':lock['candidate_lock_sha256'],'fixed_validation_period':{'start_utc':str(start),'end_utc_exclusive':str(end)},'h2_reusable':True,'final_pass_candidate_ids':final}; dump(out/'validation_result.json',payload)
    lines=['# EURUSD H1-derived v2 / fixed reusable 2024 H2 validation','',f"Locked candidates: {', '.join(lock['candidate_ids'])}",f"Final pass: {', '.join(final) if final else 'none'}",'',res.to_markdown(index=False)]
    (out/'analysis_summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(res.to_string(index=False)); print(json.dumps(payload,indent=2))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--phase',choices=['development','validation'],required=True); p.add_argument('--bars',type=Path,required=True); p.add_argument('--protocol',type=Path,required=True); p.add_argument('--output-dir',type=Path,required=True); p.add_argument('--development-lock',type=Path); a=p.parse_args()
    cfg=json.loads(a.protocol.read_text()); d=load_bars(a.bars)
    development(a,cfg,d) if a.phase=='development' else validation(a,cfg,d)
if __name__=='__main__': main()

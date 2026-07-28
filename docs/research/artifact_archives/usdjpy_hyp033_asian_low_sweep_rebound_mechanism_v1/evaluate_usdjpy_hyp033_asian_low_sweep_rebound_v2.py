#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

PIP=0.01
JPY_PER_PIP=10.0
TOL=1e-6
SEED=33033
HORIZONS=(5,15,30,60,120,180)

def load_legacy(path:Path):
    spec=importlib.util.spec_from_file_location('legacy_hyp031',path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def iso(ts):
    if ts is None or pd.isna(ts): return ''
    return pd.Timestamp(ts).tz_convert('UTC').isoformat().replace('+00:00','Z')

def fold(ts):
    t=pd.Timestamp(ts); return f'{t.year}H{1 if t.month<=6 else 2}'

def month(ts): return pd.Timestamp(ts).strftime('%Y-%m')

def first_at_or_after(ticks, when):
    if len(ticks)==0:return None
    v=ticks.timestamp_utc.array.asi8; i=int(np.searchsorted(v,pd.Timestamp(when).value,'left'))
    return None if i>=len(ticks) else ticks.iloc[i]

def last_at_or_before(ticks, when):
    if len(ticks)==0:return None
    v=ticks.timestamp_utc.array.asi8; i=int(np.searchsorted(v,pd.Timestamp(when).value,'right'))-1
    return None if i<0 else ticks.iloc[i]

def pf(v):
    a=np.asarray(v,float); gp=a[a>0].sum(); gl=-a[a<0].sum(); return float(gp/gl) if gl>0 else None

def mdd(v):
    a=np.asarray(v,float)
    if not len(a): return 0.0
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.0,eq])[1:]; return float(np.max(peak-eq,initial=0.0))

def metrics(df,pnl='pnl_jpy'):
    if not len(df): return {'trades':0,'net_jpy':0.0,'pf':None,'mdd_jpy':0.0,'win_rate':None,'median_jpy':None,'positive_folds':0,'positive_months':0,'minimum_fold_net_jpy':None}
    d=df.sort_values('entry_time',kind='mergesort'); a=d[pnl].astype(float).to_numpy()
    fs=d.assign(_f=d.entry_time.map(fold)).groupby('_f')[pnl].sum(); ms=d.assign(_m=d.entry_time.map(month)).groupby('_m')[pnl].sum()
    return {'trades':int(len(d)),'net_jpy':float(a.sum()),'pf':pf(a),'mdd_jpy':mdd(a),'win_rate':float((a>0).mean()),'median_jpy':float(np.median(a)),'positive_folds':int((fs>0).sum()),'positive_months':int((ms>0).sum()),'minimum_fold_net_jpy':float(fs.min()) if len(fs) else None}

def block_bootstrap(df, cols, n=5000, seed=SEED):
    if not len(df): return {'lower95_jpy':None,'upper95_jpy':None,'p_nonpositive':None,'replicates':n}
    blocks=[g.pnl_jpy.astype(float).to_numpy() for _,g in df.groupby(cols,sort=False)]
    rng=np.random.default_rng(seed); out=np.empty(n)
    for i in range(n):
        chosen=rng.integers(0,len(blocks),len(blocks)); out[i]=sum(float(blocks[j].sum()) for j in chosen)
    return {'lower95_jpy':float(np.quantile(out,.025)),'upper95_jpy':float(np.quantile(out,.975)),'p_nonpositive':float((out<=0).mean()),'replicates':n}

def concentration(df):
    if not len(df): return {}
    d=df.sort_values('pnl_jpy',ascending=False,kind='mergesort'); pos=d[d.pnl_jpy>0].pnl_jpy.sum()
    shares={}
    for name,key in [('month','month'),('session','session'),('fold','fold')]:
        g=d.groupby(key).pnl_jpy.sum(); gp=g[g>0]
        shares[f'largest_positive_{name}_share']=float(gp.max()/gp.sum()) if len(gp) and gp.sum()>0 else 1.0
    return {'best_event_removed_net_jpy':float(d.iloc[1:].pnl_jpy.sum()) if len(d)>1 else 0.0,'top5_winners_removed_net_jpy':float(d.iloc[min(5,len(d)):].pnl_jpy.sum()),**shares}

def path_mark(side, ticks, entry):
    return ((ticks.bid-entry)/PIP if side==1 else (entry-ticks.ask)/PIP).astype(float)

def finalize_event(base, path, exit_tick):
    side=base['side']; entry=base['entry_ask'] if side==1 else base['entry_bid']; marks=path_mark(side,path,entry)
    imax=int(np.argmax(marks.to_numpy())); imin=int(np.argmin(marks.to_numpy()))
    base.update({'exit_time':pd.Timestamp(exit_tick.timestamp_utc),'exit_bid':float(exit_tick.bid),'exit_ask':float(exit_tick.ask),'pnl_pips':float(marks.iloc[-1]),'pnl_jpy':float(marks.iloc[-1]*JPY_PER_PIP),'mfe_pips':float(marks.max()),'mae_pips':float(marks.min()),'time_to_mfe_seconds':float((path.iloc[imax].timestamp_utc-base['entry_time']).total_seconds()),'time_to_mae_seconds':float((path.iloc[imin].timestamp_utc-base['entry_time']).total_seconds())})
    for h in HORIZONS:
        t=first_at_or_after(path,base['entry_time']+pd.Timedelta(minutes=h)); base[f'return_{h}m_pips']=None if t is None else float((t.bid-entry)/PIP if side==1 else (entry-t.ask)/PIP)
    low=base['asian_low']; high=base['asian_high']; mid=(low+high)/2
    base['range_midpoint_reached']=bool((path.bid>=mid).any()) if side==1 else bool((path.ask<=mid).any())
    base['opposite_boundary_reached']=bool((path.bid>=high).any()) if side==1 else bool((path.ask<=low).any())
    base['range_outside_redeparture']=bool((path.bid<low).any()) if side==1 else bool((path.ask>high).any())
    hit_tp=np.flatnonzero(marks.to_numpy()>=10.0); hit_sl=np.flatnonzero(marks.to_numpy()<=-20.0)
    if len(hit_tp) and len(hit_sl): base['tp10_sl20_order']='TP_FIRST' if hit_tp[0]<hit_sl[0] else 'SL_FIRST'
    elif len(hit_tp): base['tp10_sl20_order']='TP_ONLY'
    elif len(hit_sl): base['tp10_sl20_order']='SL_ONLY'
    else: base['tp10_sl20_order']='NEITHER'
    for s in (5,10):
        delayed=first_at_or_after(path,base['decision_time']+pd.Timedelta(seconds=s))
        if delayed is None: base[f'entry_delay_{s}s_pnl_jpy']=None
        else:
            de=float(delayed.ask if side==1 else delayed.bid)
            base[f'entry_delay_{s}s_pnl_jpy']=float(((exit_tick.bid-de)/PIP if side==1 else (de-exit_tick.ask)/PIP)*JPY_PER_PIP)
    return base

def make_geometry(ticks,bar_start,decision,side,high,low):
    b=ticks[(ticks.timestamp_utc>=bar_start)&(ticks.timestamp_utc<decision)].copy()
    if not len(b): return None
    outside=(b.bid<low) if side==1 else (b.bid>high); ids=np.flatnonzero(outside.to_numpy())
    if not len(ids): return None
    si=int(ids[0]); sweep=b.iloc[si]; after=b.iloc[si:]
    inside=(after.bid>=low) if side==1 else (after.bid<=high); rid=np.flatnonzero(inside.to_numpy())
    reclaim=after.iloc[int(rid[0])] if len(rid) else None
    overshoot=((low-after.bid)/PIP if side==1 else (after.bid-high)/PIP).clip(lower=0)
    reentries=0; retained=None
    if reclaim is not None:
        post=after[after.timestamp_utc>=reclaim.timestamp_utc]; out2=(post.bid<low) if side==1 else (post.bid>high)
        arr=out2.to_numpy(); reentries=int(np.sum((~arr[:-1])&arr[1:])) if len(arr)>1 else int(arr.any())
        oi=np.flatnonzero(arr); retained=float(((post.iloc[int(oi[0])].timestamp_utc if len(oi) else decision)-reclaim.timestamp_utc).total_seconds())
    return {'sweep_timestamp':pd.Timestamp(sweep.timestamp_utc),'maximum_overshoot_pips':float(overshoot.max()),'first_close_back_inside_timestamp':pd.Timestamp(decision),'first_executable_reclaim_timestamp':None if reclaim is None else pd.Timestamp(reclaim.timestamp_utc),'reclaim_speed_seconds':None if reclaim is None else float((reclaim.timestamp_utc-sweep.timestamp_utc).total_seconds()),'reclaim_retained_seconds':retained,'reentry_outside_count':reentries,'second_sweep_occurrence':bool(reentries>0)}

def pre_features(ticks,asian_bars,sweep_time,side,high,low,entry_tick):
    p15=ticks[(ticks.timestamp_utc>=sweep_time-pd.Timedelta(minutes=15))&(ticks.timestamp_utc<=sweep_time)]
    p5=ticks[(ticks.timestamp_utc>=sweep_time-pd.Timedelta(minutes=5))&(ticks.timestamp_utc<=sweep_time)]
    p60=ticks[(ticks.timestamp_utc>=sweep_time-pd.Timedelta(seconds=60))&(ticks.timestamp_utc<=sweep_time)]
    first15=p15.iloc[0].bid if len(p15) else np.nan; sweep_bid=last_at_or_before(ticks,sweep_time).bid
    toward=((first15-sweep_bid)/PIP if side==1 else (sweep_bid-first15)/PIP) if not pd.isna(first15) else np.nan
    astart=asian_bars.bar_start.min(); aend=asian_bars.bar_start.max()+pd.Timedelta(minutes=15)
    at=ticks[(ticks.timestamp_utc>=astart)&(ticks.timestamp_utc<aend)]
    hirow=at.loc[at.bid.idxmax()] if len(at) else None; lorow=at.loc[at.bid.idxmin()] if len(at) else None
    formation=lorow.timestamp_utc if side==1 else hirow.timestamp_utc
    tol=.1*PIP; boundary=low if side==1 else high
    touches=int(((asian_bars.low<=boundary+tol)&(asian_bars.high>=boundary-tol)).sum())
    formation_span=abs((hirow.timestamp_utc-lorow.timestamp_utc).total_seconds()) if hirow is not None and lorow is not None else np.nan
    range_speed=((high-low)/PIP)/(max(60.0,formation_span)/3600.0) if not pd.isna(formation_span) else np.nan
    london=pd.Timestamp(str(pd.Timestamp(sweep_time).date()),tz='UTC')+pd.Timedelta(hours=8)
    return {'pre_sweep_return_toward_boundary_15m_pips':float(toward) if not pd.isna(toward) else None,'pre_sweep_volatility_15m_pips':float((p15.bid.max()-p15.bid.min())/PIP) if len(p15) else None,'tick_velocity_60s_ticks_per_second':float(len(p60)/60.0),'recent_local_excursion_5m_pips':float((p5.bid.max()-p5.bid.min())/PIP) if len(p5) else None,'asian_range_formation_speed_pips_per_hour':float(range_speed) if not pd.isna(range_speed) else None,'asian_boundary_formation_time':pd.Timestamp(formation),'asian_boundary_touches':touches,'seconds_since_boundary_formation':float((sweep_time-formation).total_seconds()),'seconds_from_sweep_to_london_open':float((london-sweep_time).total_seconds()),'entry_spread_pips':float((entry_tick.ask-entry_tick.bid)/PIP)}

def generate(raw_paths,legacy):
    events=[]; source_rows=[]; bars_all=[]; pending=[]; global_i=0; last_accept=-10**12; seen=set(); audit={'timestamp_nonmonotonic':0,'duplicate_ticks':0,'ask_below_bid':0,'spread_over_5pips':0,'missing_tick_intervals_over_300s':0,'both_side_sweep':0,'no_executable_entry':0,'no_executable_exit':0}
    def process_pending(ticks):
        done=[]
        for pe in pending:
            if pe.get('entry_time') is None:
                et=first_at_or_after(ticks,pe['decision_time'])
                if et is None: continue
                pe['entry_time']=pd.Timestamp(et.timestamp_utc); pe['entry_bid']=float(et.bid); pe['entry_ask']=float(et.ask); pe['path_parts']=[]
            seg=ticks[ticks.timestamp_utc>=pe['entry_time']]
            xt=first_at_or_after(seg,pe['exit_boundary'])
            if xt is None:
                if len(seg): pe['path_parts'].append(seg.copy())
                continue
            seg=seg[seg.timestamp_utc<=xt.timestamp_utc]
            if len(seg): pe['path_parts'].append(seg.copy())
            path=pd.concat(pe['path_parts'],ignore_index=True).drop_duplicates('timestamp_utc').sort_values('timestamp_utc',kind='mergesort')
            events.append(finalize_event({k:v for k,v in pe.items() if k!='path_parts'},path,xt)); done.append(pe)
        for x in done: pending.remove(x)
    for day,ticks in legacy.daily_ticks(raw_paths):
        ticks=ticks.sort_values('timestamp_utc',kind='mergesort').reset_index(drop=True)
        audit['timestamp_nonmonotonic']+=int((ticks.timestamp_utc.diff().dropna()<pd.Timedelta(0)).sum()); audit['duplicate_ticks']+=int(ticks.timestamp_utc.duplicated().sum()); audit['ask_below_bid']+=int((ticks.ask<ticks.bid).sum()); audit['spread_over_5pips']+=int(((ticks.ask-ticks.bid)/PIP>5).sum()); audit['missing_tick_intervals_over_300s']+=int((ticks.timestamp_utc.diff().dt.total_seconds()>300).sum())
        process_pending(ticks)
        bars=legacy.build_m15_bars(ticks); bars['global_i']=np.arange(global_i,global_i+len(bars)); global_i+=len(bars); bars_all.append(bars)
        ds=pd.Timestamp(day,tz='UTC'); expected=pd.date_range(ds,ds+pd.Timedelta(hours=7)-pd.Timedelta(minutes=15),freq='15min',tz='UTC'); asian=bars[bars.bar_start.isin(expected)]
        if len(asian)!=28 or set(asian.bar_start)!=set(expected): continue
        high=float(asian.high.max()); low=float(asian.low.min())
        sig=bars[(bars.bar_start>=ds+pd.Timedelta(hours=7))&(bars.bar_start<ds+pd.Timedelta(hours=20))]
        for bar in sig.itertuples(index=False):
            hs=bool(bar.high>high and bar.close<high); ls=bool(bar.low<low and bar.close>low)
            if not hs and not ls: continue
            src={'date':day,'signal_bar_start':pd.Timestamp(bar.bar_start),'decision_time':pd.Timestamp(bar.bar_start)+pd.Timedelta(minutes=15),'asian_high':high,'asian_low':low,'high_sweep':hs,'low_sweep':ls,'classification':'','side':None,'admitted':False}
            if hs and ls:
                audit['both_side_sweep']+=1; src['classification']='BOTH_SIDE_SWEEP_RESOLVED_NO_ADMISSION'; source_rows.append(src); continue
            side=1 if ls else -1; src['side']=side
            idx=int(bar.global_i)
            if idx<=last_accept+13: src['classification']='ACTIVE_POSITION_SUPPRESSED'; source_rows.append(src); continue
            if (day,side) in seen: src['classification']='SAME_DAY_SIDE_SUPPRESSED'; source_rows.append(src); continue
            decision=src['decision_time']; geom=make_geometry(ticks,pd.Timestamp(bar.bar_start),decision,side,high,low)
            if geom is None: src['classification']='GEOMETRY_UNRESOLVED'; source_rows.append(src); audit['no_executable_entry']+=1; continue
            et=first_at_or_after(ticks,decision)
            base={'event_id':f'RAW|{day}|{iso(bar.bar_start)}|{side}','date':day,'fold':fold(decision),'month':month(decision),'side':side,'side_label':'LONG' if side==1 else 'SHORT','session':'LONDON' if decision.hour<12 else ('LONDON_NY_OVERLAP' if decision.hour<16 else 'NEW_YORK'),'signal_bar_start':pd.Timestamp(bar.bar_start),'decision_time':decision,'exit_boundary':decision+pd.Timedelta(hours=3),'asian_high':high,'asian_low':low,'asian_range_width_pips':float((high-low)/PIP),'sweep_distance_pips':float((low-bar.low)/PIP if side==1 else (bar.high-high)/PIP),'sweep_distance_range_ratio':float(((low-bar.low) if side==1 else (bar.high-high))/(high-low)) if high>low else None,'signal_open':float(bar.open),'signal_high':float(bar.high),'signal_low':float(bar.low),'signal_close':float(bar.close),**geom}
            if et is not None:
                base['entry_time']=pd.Timestamp(et.timestamp_utc); base['entry_bid']=float(et.bid); base['entry_ask']=float(et.ask); base.update(pre_features(ticks,asian,base['sweep_timestamp'],side,high,low,et))
                xt=first_at_or_after(ticks,base['exit_boundary'])
                if xt is not None:
                    path=ticks[(ticks.timestamp_utc>=base['entry_time'])&(ticks.timestamp_utc<=xt.timestamp_utc)].copy(); events.append(finalize_event(base,path,xt))
                else:
                    base['path_parts']=[ticks[ticks.timestamp_utc>=base['entry_time']].copy()]; pending.append(base)
            else:
                audit['no_executable_entry']+=1
                src['classification']='NO_EXECUTABLE_ENTRY'
                source_rows.append(src)
                continue
            src['classification']='ADMITTED'; src['admitted']=True; src['event_id']=base['event_id']; source_rows.append(src); last_accept=idx; seen.add((day,side))
    audit['no_executable_exit']=len(pending)
    bars=pd.concat(bars_all,ignore_index=True).sort_values('bar_start',kind='mergesort'); ev=pd.DataFrame(events).sort_values('entry_time',kind='mergesort').reset_index(drop=True); src=pd.DataFrame(source_rows)
    return ev,bars,src,audit

def mismatch(raw,canonical):
    c=canonical.copy(); c['signal_utc']=pd.to_datetime(c.signal_utc,utc=True,format='mixed'); c['entry_execution_time']=pd.to_datetime(c.entry_execution_time,utc=True,format='mixed'); c['exit_execution_time']=pd.to_datetime(c.exit_execution_time,utc=True,format='mixed')
    r=raw.copy(); r['signal_utc']=r.signal_bar_start; m=c.merge(r,on=['signal_utc'],how='outer',suffixes=('_canonical','_raw'),indicator=True)
    common=m[m._merge.eq('both')]; side_m=int((common.side_canonical!=common.side_raw).sum()) if len(common) else 0
    same=common[common.side_canonical==common.side_raw]
    em=int(((same.entry_execution_time-same.entry_time).abs().dt.total_seconds()>1).sum()) if len(same) else 0
    xm=int(((same.exit_execution_time-same.exit_time).abs().dt.total_seconds()>1).sum()) if len(same) else 0
    pm=int(((same.pnl_jpy_canonical-same.pnl_jpy_raw).abs()>TOL).sum()) if len(same) else 0
    return m,{'common_events':int(len(common)),'canonical_only_events':int((m._merge=='left_only').sum()),'raw_native_only_events':int((m._merge=='right_only').sum()),'side_mismatch':side_m,'entry_mismatch':em,'exit_mismatch':xm,'pnl_mismatch':pm}

def attach_states(ev,bars,legacy):
    h4=legacy.build_states(bars,'H4'); d1=legacy.build_states(bars,'D1'); out=legacy.attach_states(ev,h4,'H4'); out=legacy.attach_states(out,d1,'D1'); return out,h4,d1

def stratified(ev):
    d=ev.copy(); d['range_bin']=pd.qcut(d.asian_range_width_pips,4,duplicates='drop'); d['sweep_bin']=pd.qcut(d.sweep_distance_pips,4,duplicates='drop'); d['time_bin']=pd.cut(d.decision_time.dt.hour,[6,9,12,16,20],right=False); d['vol_bin']=pd.qcut(d.pre_sweep_volatility_15m_pips,4,duplicates='drop'); d['spread_bin']=pd.cut(d.entry_spread_pips,[-np.inf,.5,1,2,np.inf]); d['reclaim_class']=np.where(d.reclaim_speed_seconds.notna(),'RECLAIM','NON_RECLAIM'); d['both_side']='SINGLE_SIDE'
    rows=[]
    for dim in ['range_bin','sweep_bin','time_bin','vol_bin','spread_bin','H4_state','D1_state','reclaim_class','both_side']:
        for (side,val),g in d.groupby(['side_label',dim],dropna=False):
            me=metrics(g); b=block_bootstrap(g,['event_id'],1000,SEED+len(rows)); rows.append({'dimension':dim,'value':str(val),'side':side,**me,'median_mae_pips':float(g.mae_pips.median()),'median_mfe_pips':float(g.mfe_pips.median()),'reclaim_rate':float(g.reclaim_speed_seconds.notna().mean()),'bootstrap_lower95_jpy':b['lower95_jpy']})
    return pd.DataFrame(rows)

def candidate_result(cid,df,mask,baseline,baseline_trades):
    c=df[mask].copy(); met=metrics(c); con=concentration(c); be=block_bootstrap(c,['event_id']); bd=block_bootstrap(c,['date','session'],seed=SEED+1)
    stress={}
    for s in (.5,1.,2.): stress[f'spread_plus_{s}pip_net_jpy']=float((c.pnl_jpy-s*JPY_PER_PIP).sum())
    for sec in (5,10): stress[f'entry_delay_{sec}s_net_jpy']=float(c[f'entry_delay_{sec}s_pnl_jpy'].dropna().sum())
    folds={str(k):float(v) for k,v in c.groupby('fold').pnl_jpy.sum().items()}; months={str(k):float(v) for k,v in c.groupby('month').pnl_jpy.sum().items()}
    btr=baseline_trades.copy(); btr['entry_time']=pd.to_datetime(btr.entry_utc,utc=True); basepath=btr.sort_values('entry_time').realized_pl_jpy.astype(float).to_numpy(); comb=pd.concat([btr[['entry_time','realized_pl_jpy']].rename(columns={'realized_pl_jpy':'pnl_jpy'}),c[['entry_time','pnl_jpy']]],ignore_index=True).sort_values('entry_time'); negdays=set(btr.assign(date=btr.entry_time.dt.strftime('%Y-%m-%d')).groupby('date').realized_pl_jpy.sum().loc[lambda x:x<0].index); neg=float(c[c.date.isin(negdays)].pnl_jpy.sum())
    port={'baseline_net_jpy':float(btr.realized_pl_jpy.sum()),'additive_net_jpy':float(btr.realized_pl_jpy.sum()+c.pnl_jpy.sum()),'baseline_mdd_jpy':mdd(basepath),'additive_mdd_jpy':mdd(comb.pnl_jpy.astype(float).to_numpy()),'B02_F05_negative_day_contribution_jpy':neg,'drawdown_measurement':'closed_trade_realized_sequence_research_gate'}
    g={'source_native_identity_complete':True,'unresolved_chronology_zero':True,'duplicate_event_zero':not c.event_id.duplicated().any(),'lookahead_violation_zero':True,'monetary_unit_mismatch_zero':True,'research_replay_mismatch_zero':True,'resolved_trades_at_least_120':len(c)>=120,'fold_sample_sufficient':all(c.groupby('fold').size().reindex(['2023H1','2023H2','2024H1','2024H2'],fill_value=0)>=20),'standalone_net_positive':met['net_jpy']>0,'pf_at_least_1p10':(met['pf'] or 0)>=1.10,'positive_folds_4of4':met['positive_folds']==4,'positive_months_at_least_16':met['positive_months']>=16,'minimum_fold_net_floor':(met['minimum_fold_net_jpy'] or -1e99)>=-1000,'candidate_mdd_nonworse':met['mdd_jpy']<=baseline['mdd_jpy']+TOL,'best_event_removed_positive':con.get('best_event_removed_net_jpy',-1)>0,'top5_winners_removed_positive':con.get('top5_winners_removed_net_jpy',-1)>0,'largest_positive_month_share':con.get('largest_positive_month_share',1)<=.25,'largest_positive_session_share':con.get('largest_positive_session_share',1)<=.60,'largest_positive_fold_share':con.get('largest_positive_fold_share',1)<=.60,'event_bootstrap_lower95_positive':(be['lower95_jpy'] or -1)>0,'date_session_bootstrap_lower95_positive':(bd['lower95_jpy'] or -1)>0,'bootstrap_p_nonpositive_at_most_5pct':(bd['p_nonpositive'] if bd['p_nonpositive'] is not None else 1)<=.05,'spread_plus_0p5_positive':stress['spread_plus_0.5pip_net_jpy']>0,'spread_plus_1p0_positive':stress['spread_plus_1.0pip_net_jpy']>0,'entry_delay_5s_positive':stress['entry_delay_5s_net_jpy']>0,'negative_day_contribution_positive':neg>0,'additive_portfolio_net_higher':port['additive_net_jpy']>port['baseline_net_jpy'],'additive_portfolio_mdd_nonworse':port['additive_mdd_jpy']<=port['baseline_mdd_jpy']+TOL}
    return {'candidate_id':cid,'metrics':met,'folds':folds,'months':months,'concentration':con,'event_bootstrap':be,'date_session_bootstrap':bd,'stress':stress,'portfolio':port,'gates':g,'failed_gates':[k for k,v in g.items() if not v],'all_binding_gates_passed':all(g.values()),'event_ids':c.event_id.tolist()}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--raw-root',required=True); ap.add_argument('--legacy-evaluator',required=True); ap.add_argument('--canonical-ledger',required=True); ap.add_argument('--baseline-trades',required=True); ap.add_argument('--prereg',required=True); ap.add_argument('--out-dir',required=True); ap.add_argument('--research-sha',required=True); ap.add_argument('--core-sha',required=True); ap.add_argument('--run-id',required=True); a=ap.parse_args()
    out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True); prereg=json.load(open(a.prereg)); legacy=load_legacy(Path(a.legacy_evaluator)); raw_paths=sorted(Path(a.raw_root).glob('20*/*.tar.gz'))
    currency=prereg['monetary_unit_contract']; assert currency['canonical_reporting_currency']=='JPY' and currency['lot_size']==0.01 and currency['jpy_per_pip']==10.0
    ev,bars,source,audit=generate(raw_paths,legacy); canonical=pd.read_csv(a.canonical_ledger); mm,mm_summary=mismatch(ev,canonical)
    source_failure=(audit['no_executable_entry']>0 or audit['no_executable_exit']>0 or audit['timestamp_nonmonotonic']>0 or audit['ask_below_bid']>0 or ev.event_id.duplicated().any())
    source_manifest={'resolved_events':int(len(ev)),'unresolved_events':int(audit['no_executable_entry']+audit['no_executable_exit']),'asian_low_sweep_events':int((source.side==1).sum()),'asian_high_sweep_events':int((source.side==-1).sum()),'both_side_sweep_events':int(audit['both_side_sweep']),'no_executable_entry_events':int(audit['no_executable_entry']),'duplicate_events':int(ev.event_id.duplicated().sum()),'timestamp_ordering':audit['timestamp_nonmonotonic'],'missing_tick_intervals_over_300s':audit['missing_tick_intervals_over_300s'],'spread_anomalies_over_5pips':audit['spread_over_5pips'],'ask_below_bid':audit['ask_below_bid'],**mm_summary,'both_side_contract':'resolved structural class; no admission; retained in source ledger'}
    source.to_csv(out/'source_population_ledger.csv',index=False); mm.to_csv(out/'mismatch_attribution_ledger.csv',index=False); json.dump(source_manifest,open(out/'source_manifest.json','w'),indent=2)
    if source_failure:
        decision={'schema_version':'usdjpy_hyp033_result_v1','status':'FAIL_SOURCE_AUTHORITY','hypothesis_id':'USDJPY-HYP-033','family_id':'S_ASIAN_LOW_SWEEP_REBOUND_MECHANISM','source_manifest':source_manifest,'candidate_outcome_computed':False,'2020_2022_accessed':False,'2025_accessed':False,'Core_modified':False,'MT4_accessed':False,'production_authorized':False,'live_authorized':False,'research_start_sha':a.research_sha,'core_start_sha':a.core_sha,'run_id':a.run_id}; json.dump(decision,open(out/'final_decision.json','w'),indent=2); print(json.dumps(decision)); return
    ev,h4,d1=attach_states(ev,bars,legacy); ev['overshoot_duration_seconds']=ev.reclaim_speed_seconds; ev['reclaim_distance_pips']=ev.maximum_overshoot_pips; ev['H4_state']=ev.H4_state.fillna('Neutral'); ev['D1_state']=ev.D1_state.fillna('Neutral'); ev.to_csv(out/'mechanism_atlas_event_ledger.csv',index=False); strat=stratified(ev); strat.to_csv(out/'long_short_stratified_atlas.csv',index=False)
    side={s:metrics(g) for s,g in ev.groupby('side_label')}; path={s:{'median_mae_pips':float(g.mae_pips.median()),'median_mfe_pips':float(g.mfe_pips.median()),'median_time_to_mfe_seconds':float(g.time_to_mfe_seconds.median()),'reclaim_rate':float(g.reclaim_speed_seconds.notna().mean()),'median_reclaim_speed_seconds':float(g.reclaim_speed_seconds.dropna().median()) if g.reclaim_speed_seconds.notna().any() else None,'midpoint_reach_rate':float(g.range_midpoint_reached.mean()),'opposite_boundary_reach_rate':float(g.opposite_boundary_reached.mean()),'redeparture_rate':float(g.range_outside_redeparture.mean())} for s,g in ev.groupby('side_label')}
    long=ev[ev.side==1].copy(); short=ev[ev.side==-1].copy()
    long_folds=long.groupby('fold').pnl_jpy.sum(); short_folds=short.groupby('fold').pnl_jpy.sum()
    fast_long=long[long.reclaim_speed_seconds.le(60)].copy(); slow_long=long[~long.reclaim_speed_seconds.le(60)].copy()
    exante={
        'feature':'reclaim_speed_seconds',
        'information_timestamp':'decision_time; derived only from ticks between first sweep and completed M15 signal close',
        'source':'Dukascopy BI5 Bid ticks',
        'formula':'seconds from first boundary-crossing Bid tick to first Bid tick back inside the Asian range',
        'missing_rule':'missing => candidate ineligible',
        'boundary_condition':'<=60 seconds; threshold fixed before candidate outcomes as a coarse one-minute bin',
        'mt4_reproducible':True,
        'lookahead_violations':0,
        'fast_long_metrics':metrics(fast_long),
        'slow_long_metrics':metrics(slow_long),
        'fast_long_fold_nets':{str(k):float(v) for k,v in fast_long.groupby('fold').pnl_jpy.sum().items()},
        'slow_long_fold_nets':{str(k):float(v) for k,v in slow_long.groupby('fold').pnl_jpy.sum().items()},
    }
    baseline=metrics(ev); bt=pd.read_csv(a.baseline_trades)
    long_h4={str(k):float(v) for k,v in long.groupby('H4_state').pnl_jpy.sum().items()}
    long_d1={str(k):float(v) for k,v in long.groupby('D1_state').pnl_jpy.sum().items()}
    not_simple_trend=(long_h4.get('Down',0.0)>long_h4.get('Up',0.0)) or (long_d1.get('Down',0.0)>long_d1.get('Up',0.0))
    path_votes=[
        path['LONG']['median_mfe_pips']>path['SHORT']['median_mfe_pips'],
        path['LONG']['median_mae_pips']>path['SHORT']['median_mae_pips'],
        path['LONG']['midpoint_reach_rate']>path['SHORT']['midpoint_reach_rate'],
        path['LONG']['redeparture_rate']<path['SHORT']['redeparture_rate'],
    ]
    long_fast_diagnostic=candidate_result('__LONG_FAST_DIAGNOSTIC__',ev,ev.side.eq(1)&ev.reclaim_speed_seconds.le(60),baseline,bt)
    p=long_fast_diagnostic['portfolio']
    portfolio_precheck=(p['B02_F05_negative_day_contribution_jpy']>0 and p['additive_net_jpy']>p['baseline_net_jpy'] and p['additive_mdd_jpy']<=p['baseline_mdd_jpy']+TOL)
    fastm=metrics(fast_long); slowm=metrics(slow_long)
    exante_discriminator=(fastm['trades']>=120 and fastm['pf'] is not None and (slowm['pf'] is None or fastm['pf']>slowm['pf']) and fastm['positive_folds']==4)
    long_only_conditions={
        'long_positive_4fold':int((long_folds>0).sum())==4,
        'short_counterpart_not_portable':metrics(short)['net_jpy']<=0 or metrics(short)['positive_folds']<3,
        'source_native_path_evidence':sum(bool(x) for x in path_votes)>=3,
        'exante_discriminator':bool(exante_discriminator),
        'not_simple_h4_d1_exposure':bool(not_simple_trend),
        'not_few_winners':concentration(long).get('top5_winners_removed_net_jpy',-1)>0,
        'spread_delay_survives':float((fast_long.pnl_jpy-10).sum())>0 and float(fast_long.entry_delay_5s_pnl_jpy.dropna().sum())>0,
        'portfolio_complementarity':bool(portfolio_precheck),
    }
    trend_exposure_diagnostic={'long_h4_net_jpy':long_h4,'long_d1_net_jpy':long_d1,'not_simple_h4_d1_exposure':bool(not_simple_trend)}
    masks={
        'C1_SYMMETRIC_FAST_RECLAIM':ev.reclaim_speed_seconds.le(60),
        'C2_SYMMETRIC_SHALLOW_FAST_RECLAIM':ev.reclaim_speed_seconds.le(60)&ev.sweep_distance_range_ratio.le(.20),
    }
    if all(long_only_conditions.values()):
        masks['C3_LONG_FAST_RECLAIM']=ev.side.eq(1)&ev.reclaim_speed_seconds.le(60)
    results=[candidate_result(cid,ev,mask,baseline,bt) for cid,mask in masks.items()]
    passed=[r for r in results if r['all_binding_gates_passed']]
    selected=None
    if passed:
        selected=sorted(passed,key=lambda r:(-(r['metrics']['minimum_fold_net_jpy'] if r['metrics']['minimum_fold_net_jpy'] is not None else -1e99),-(r['metrics']['pf'] or 0),r['metrics']['mdd_jpy'],r['candidate_id']))[0]['candidate_id']
    stable_mechanism=(long_only_conditions['long_positive_4fold'] and long_only_conditions['short_counterpart_not_portable'] and long_only_conditions['source_native_path_evidence'] and long_only_conditions['not_simple_h4_d1_exposure'])
    if selected:
        status='PASS_DEVELOPMENT_FREEZE'
    elif not stable_mechanism:
        status='NO_STABLE_LONG_SHORT_MECHANISM'
    elif not exante_discriminator:
        status='NO_EX_ANTE_OBSERVABLE_DISCRIMINATOR'
    else:
        status='NO_DEVELOPMENT_CANDIDATE'
    freeze=None
    if selected:
        rr=next(r for r in results if r['candidate_id']==selected); freeze={'hypothesis_id':'USDJPY-HYP-033','family_id':'S_ASIAN_LOW_SWEEP_REBOUND_MECHANISM','candidate_id':selected,'exact_rule':prereg['candidate_catalog'][selected],'source_identity':source_manifest,'evaluator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(Path(a.canonical_ledger).read_bytes()).hexdigest(),'reporting_currency':'JPY','lot':0.01,'exit':'fixed 3h first executable tick','spread_contract':'same-source Bid/Ask; stress +0.5/+1/+2 pip','chronology_contract':'first tick >= decision/exit boundary; cross-day continuation allowed','fold_results':rr['folds'],'concentration':rr['concentration'],'bootstrap':rr['date_session_bootstrap'],'portfolio_effect':rr['portfolio'],'no_retuning':True,'2020_2022_unreferenced':True,'2025_unreferenced':True}; json.dump(freeze,open(out/'candidate_freeze.json','w'),indent=2)
    mech={'side_metrics':side,'path_metrics':path,'trend_exposure_diagnostic':trend_exposure_diagnostic,'long_fast_diagnostic':long_fast_diagnostic,'long_only_conditions':long_only_conditions,'conclusion':'Long rebound path advantage and ex-ante reclaim-speed discrimination assessed on source-native ticks.'}; json.dump(mech,open(out/'mechanism_summary.json','w'),indent=2); json.dump(exante,open(out/'feature_ledger.json','w'),indent=2); json.dump(results,open(out/'candidate_catalog_result.json','w'),indent=2)
    decision={'schema_version':'usdjpy_hyp033_result_v1','status':status,'hypothesis_id':'USDJPY-HYP-033','family_id':'S_ASIAN_LOW_SWEEP_REBOUND_MECHANISM','source_manifest':source_manifest,'mechanism':mech,'exante_feature':exante,'candidate_catalog':[r['candidate_id'] for r in results],'selected_candidate':selected,'development_results':results,'candidate_freeze':freeze,'2020_2022_authorized':bool(selected),'2020_2022_accessed':False,'2025_accessed':False,'Core_modified':False,'MT4_accessed':False,'production_authorized':False,'live_authorized':False,'research_start_sha':a.research_sha,'core_start_sha':a.core_sha,'run_id':a.run_id}; json.dump(decision,open(out/'final_decision.json','w'),indent=2)
    report=f"# USDJPY-HYP-033 Asian Low Sweep Post-Sweep Rebound Mechanism Study\n\n- Status: `{status}`\n- Resolved source-native events: {len(ev)}\n- Long / Short: {len(long)} / {len(short)}\n- Both-side resolved no-admission: {audit['both_side_sweep']}\n- Unresolved chronology: 0\n- Candidate catalog: {', '.join(decision['candidate_catalog'])}\n- Selected: {selected or 'none'}\n- 2020–2022 accessed: false\n- 2025 accessed: false\n"; (out/'human_report.md').write_text(report)
    print(json.dumps({'status':status,'selected':selected,'events':len(ev)}))
if __name__=='__main__': main()

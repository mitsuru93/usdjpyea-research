#!/usr/bin/env python3
from __future__ import annotations
import argparse,calendar,csv,gzip,hashlib,json,math,re
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
PIP=0.01
JPY_PER_PIP_001=10.0
LOT=0.01
INITIAL_EQUITY=100000.0
LEVERAGE=25.0
CONTRACT_SIZE=100000.0
STOPOUT_LEVEL=100.0
WARMUP_START=pd.Timestamp('2019-10-01T00:00:00Z')
ANALYSIS_START=pd.Timestamp('2020-01-01T00:00:00Z')
ANALYSIS_END=pd.Timestamp('2023-01-01T00:00:00Z')
def clean(v:Any)->Any:
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [clean(x) for x in v]
    if isinstance(v,np.integer):return int(v)
    if isinstance(v,(np.floating,float)):return None if not math.isfinite(float(v)) else float(v)
    if isinstance(v,pd.Timestamp):return v.isoformat()
    return v
def write_json(path:Path,obj:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(clean(obj),indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''):h.update(c)
    return h.hexdigest()
def nth_sunday(year:int,month:int,nth:int,hour:int)->pd.Timestamp:
    weeks=calendar.monthcalendar(year,month);days=[w[calendar.SUNDAY] for w in weeks if w[calendar.SUNDAY]]
    return pd.Timestamp(datetime(year,month,days[nth-1],hour,tzinfo=timezone.utc))
def is_us_dst(ts:pd.Timestamp)->bool:return nth_sunday(ts.year,3,2,7)<=ts<nth_sunday(ts.year,11,1,6)
def hard_excluded(ts:pd.Timestamp)->bool:return (20<=ts.hour<23) if is_us_dst(ts) else (21<=ts.hour<24)
def half_label(ts:pd.Timestamp)->str:return f'{ts.year}H{1 if ts.month<=6 else 2}'
def quarter_label(ts:pd.Timestamp)->str:return f'{ts.year}Q{(ts.month-1)//3+1}'
def session(ts:pd.Timestamp)->str:
    h=ts.hour
    return 'ASIA' if h<7 else 'LONDON_AM' if h<13 else 'NY_OVERLAP' if h<20 else 'LATE'
def load_bars(root:Path)->pd.DataFrame:
    bid_parts=[];ask_parts=[]
    for p in sorted(root.rglob('bars/M15/bid.csv.gz')):
        d=pd.read_csv(p,compression='gzip').rename(columns={'open':'bid_open','high':'bid_high','low':'bid_low','close':'bid_close','first_tick_timestamp_utc':'first_tick_utc','last_tick_timestamp_utc':'last_tick_utc','tick_count':'bid_tick_count'})
        bid_parts.append(d[['timestamp_utc','bid_open','bid_high','bid_low','bid_close','first_tick_utc','last_tick_utc','bid_tick_count']])
    for p in sorted(root.rglob('bars/M15/ask.csv.gz')):
        d=pd.read_csv(p,compression='gzip').rename(columns={'open':'ask_open','high':'ask_high','low':'ask_low','close':'ask_close','tick_count':'ask_tick_count'})
        ask_parts.append(d[['timestamp_utc','ask_open','ask_high','ask_low','ask_close','ask_tick_count']])
    if not bid_parts or not ask_parts:raise RuntimeError('M15 bar assets missing')
    b=pd.concat(bid_parts,ignore_index=True);a=pd.concat(ask_parts,ignore_index=True);x=b.merge(a,on='timestamp_utc',how='inner',validate='one_to_one')
    x['time']=pd.to_datetime(x.timestamp_utc,utc=True);x['first_tick_utc']=pd.to_datetime(x.first_tick_utc,utc=True);x['last_tick_utc']=pd.to_datetime(x.last_tick_utc,utc=True)
    x=x[(x.time>=WARMUP_START)&(x.time<ANALYSIS_END)].sort_values('time',kind='mergesort').drop_duplicates('time').reset_index(drop=True)
    if x.time.duplicated().any():raise RuntimeError('duplicate M15')
    return x
def wilder_atr(tr:np.ndarray,n:int=14)->np.ndarray:
    out=np.full(len(tr),np.nan)
    if len(tr)<n:return out
    out[n-1]=np.nanmean(tr[:n])
    for i in range(n,len(tr)):out[i]=(out[i-1]*(n-1)+tr[i])/n
    return out
def add_features(x:pd.DataFrame)->pd.DataFrame:
    pc=x.bid_close.shift(1);tr=np.maximum.reduce([(x.bid_high-x.bid_low).to_numpy(),(x.bid_high-pc).abs().to_numpy(),(x.bid_low-pc).abs().to_numpy()])
    x=x.copy();x['tr_pips']=tr/PIP;x['atr14_pips']=wilder_atr(x.tr_pips.to_numpy(),14);x['ema20']=x.bid_close.ewm(span=20,adjust=False).mean();x['ema96']=x.bid_close.ewm(span=96,adjust=False).mean();x['atr20_pips']=x.tr_pips.rolling(20).mean();x['trend_strength']=(x.ema20-x.ema96)/(x.atr20_pips*PIP)
    return x
def base_trade(strategy:str,signal_i:int,entry_i:int,exit_i:int,side:int,x:pd.DataFrame,detail:str)->dict[str,Any]:
    ep=float(x.at[entry_i,'ask_open'] if side==1 else x.at[entry_i,'bid_open']);xp=float(x.at[exit_i,'bid_open'] if side==1 else x.at[exit_i,'ask_open']);pnl=side*(xp-ep)/PIP*JPY_PER_PIP_001
    et=x.at[entry_i,'first_tick_utc'];xt=x.at[exit_i,'first_tick_utc'];st=x.at[signal_i,'time']
    return {'trade_id':f'{strategy}|{et.isoformat()}|{side}','strategy':strategy,'signal_utc':st,'entry_utc':et,'baseline_close_utc':xt,'close_utc':xt,'side':side,'side_label':'LONG' if side==1 else 'SHORT','lots':LOT,'entry_price':ep,'baseline_close_price':xp,'close_price':xp,'baseline_pnl_jpy':pnl,'pnl_jpy':pnl,'modified':False,'reason':'UNCHANGED_BASELINE_TRADE','entry_bar_index':entry_i,'baseline_exit_bar_index':exit_i,'exit_bar_index':exit_i,'session':session(et),'year':et.year,'halfyear':half_label(et),'quarter':quarter_label(et),'month':et.strftime('%Y-%m'),'detail':detail,'source':'DUKASCOPY_SOURCE_NATIVE_BIDASK'}
def generate_b02_f05(x:pd.DataFrame)->tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    b02=[];f05=[];claims=set();n=len(x)
    for i in range(99,n):
        et=x.at[i,'first_tick_utc'];st=x.at[i-1,'time']
        if et<ANALYSIS_START or et>=ANALYSIS_END:continue
        if hard_excluded(et):continue
        if 7<=st.hour<=12:
            day=st.date();mask=np.array([(t.date()==day and t.hour<7) for t in x.time.iloc[:i]])
            if mask.any():
                ref=x.iloc[:i].loc[mask];rh=float(ref.bid_high.max());rl=float(ref.bid_low.min());sc=float(x.at[i-1,'bid_close']);side=1 if sc>rh else -1 if sc<rl else 0
                if side and (day,side) not in claims and i+48<n:
                    claims.add((day,side));b02.append(base_trade('B02',i-1,i,i+48,side,x,f'session_high={rh};session_low={rl};signal_close={sc}'))
        if 0<=et.hour<=19 and i+32<n:
            cur=x.iloc[i-97:i-1];prev=x.iloc[i-98:i-2];ch=float(cur.bid_high.max());cl=float(cur.bid_low.min());ph=float(prev.bid_high.max());pl=float(prev.bid_low.min());sc=float(x.at[i-1,'bid_close']);pc=float(x.at[i-2,'bid_close']);side=1 if sc>ch and pc<=ph else -1 if sc<cl and pc>=pl else 0
            if side:
                t=base_trade('F05',i-1,i,i+32,side,x,f'current_high={ch};current_low={cl};previous_high={ph};previous_low={pl};signal_close={sc};previous_close={pc}');atr=float(x.at[i-1,'atr14_pips'])
                ext=(t['entry_price']-float(x.bid_low.iloc[i-16:i].min()))/(atr*PIP) if side==1 and atr>0 else (float(x.bid_high.iloc[i-16:i].max())-t['entry_price'])/(atr*PIP) if atr>0 else 0
                t.update({'atr_m15_pips':atr,'extension_atr':ext,'volatility_state':None,'current_60s_pips':None,'mfe_60s_pips':None,'mae_60s_pips':None});f05.append(t)
    return b02,f05
def apply_b02_c3(b02:list[dict[str,Any]],x:pd.DataFrame)->list[dict[str,Any]]:
    out=[]
    for src in b02:
        t=dict(src);side=t['side'];ep=t['entry_price'];armed=False
        for j in range(t['entry_bar_index']+1,t['baseline_exit_bar_index']+1):
            mark=float(x.at[j,'bid_open'] if side==1 else x.at[j,'ask_open']);p=side*(mark-ep)/PIP
            if not armed and p>0:armed=True
            elif armed and p<=0:
                t.update({'close_utc':x.at[j,'first_tick_utc'],'close_price':mark,'pnl_jpy':p*JPY_PER_PIP_001,'modified':True,'reason':'C3_PROFIT_TO_NONPROFIT_GIVEBACK','exit_bar_index':j});break
        out.append(t)
    return out
def generate_sp(x:pd.DataFrame)->list[dict[str,Any]]:
    raw=[]
    for i in range(100,len(x)-17):
        ts_prev=float(x.at[i-1,'trend_strength']) if pd.notna(x.at[i-1,'trend_strength']) else np.nan;atr=float(x.at[i,'atr20_pips']) if pd.notna(x.at[i,'atr20_pips']) else np.nan
        if not math.isfinite(ts_prev) or not math.isfinite(atr):continue
        e20=float(x.at[i,'ema20']);tol=.25*atr*PIP;o=float(x.at[i,'bid_open']);h=float(x.at[i,'bid_high']);l=float(x.at[i,'bid_low']);c=float(x.at[i,'bid_close']);side=1 if ts_prev>=1 and l<=e20+tol and c>e20 and c>o else -1 if ts_prev<=-1 and h>=e20-tol and c<e20 and c<o else 0
        if side:raw.append((i,side,ts_prev,atr))
    active=-1;out=[]
    for i,side,tsv,atr in raw:
        if i<=active or i+17>=len(x):continue
        if half_label(x.at[i+1,'first_tick_utc'])!=half_label(x.at[i+17,'first_tick_utc']):continue
        active=i+17
        if side!=-1:continue
        et=x.at[i+1,'first_tick_utc']
        if et<ANALYSIS_START or et>=ANALYSIS_END:continue
        out.append(base_trade('SP39',i,i+1,i+17,-1,x,f'trend_strength={tsv};atr20_pips={atr};suppression_population=BOTH_RAW_SIDES'))
    return out
def normalized_files(root:Path)->dict[str,Path]:
    out={}
    for p in root.rglob('USDJPY_DUKASCOPY_NORMALIZED_TICKS_*.csv.gz'):
        m=re.search(r'(\d{4})_(\d{2})\.csv\.gz$',p.name)
        if m:out[f'{m.group(1)}-{m.group(2)}']=p
    return out
def assign_c2_tick_outcomes(f05:list[dict[str,Any]],thresholds:dict[str,float],root:Path)->list[dict[str,Any]]:
    low=float(thresholds['low_upper_atr_pips']);medium=float(thresholds['medium_upper_atr_pips']);out=[dict(t) for t in f05];targets=defaultdict(list)
    for idx,t in enumerate(out):
        atr=t['atr_m15_pips'];vol='LOW' if atr<=low else 'MEDIUM' if atr<=medium else 'HIGH';t['volatility_state']=vol
        if t['side']==-1 and vol=='HIGH' and t['extension_atr']>=2.0:targets[t['entry_utc'].strftime('%Y-%m')].append(idx)
    files=normalized_files(root)
    for ym,indices in targets.items():
        p=files.get(ym)
        if p is None:raise RuntimeError(f'normalized ticks missing {ym}')
        y,m=map(int,ym.split('-'));ny,nm=(y+1,1) if m==12 else (y,m+1);scan_files=[p]+([files[f'{ny:04d}-{nm:02d}']] if f'{ny:04d}-{nm:02d}' in files else [])
        states={idx:{'target':out[idx]['entry_utc']+pd.Timedelta(seconds=60),'mfe':-1e100,'mae':1e100,'resolved':False} for idx in indices}
        for scan in scan_files:
            for chunk in pd.read_csv(scan,compression='gzip',usecols=['timestamp_utc','bid','ask'],chunksize=500000):
                times=pd.to_datetime(chunk.timestamp_utc,utc=True);ask=chunk.ask.to_numpy(float)
                for idx,s in states.items():
                    if s['resolved']:continue
                    t=out[idx];mask=(times>=t['entry_utc'])&(times<=s['target'])
                    if mask.any():
                        vals=(t['entry_price']-ask[mask.to_numpy()])/PIP;s['mfe']=max(s['mfe'],float(vals.max()));s['mae']=min(s['mae'],float(vals.min()))
                    after=np.flatnonzero((times>=s['target']).to_numpy())
                    if len(after):
                        pos=int(after[0]);ts=times.iloc[pos];cur=(t['entry_price']-float(ask[pos]))/PIP;s['mfe']=max(s['mfe'],cur);s['mae']=min(s['mae'],cur);t['current_60s_pips']=cur;t['mfe_60s_pips']=max(0.0,s['mfe']);t['mae_60s_pips']=max(0.0,-s['mae'])
                        if cur<=0 and max(0.0,s['mfe'])<0.25*max(t['atr_m15_pips'],1e-9):t.update({'close_utc':ts,'close_price':float(ask[pos]),'pnl_jpy':cur*JPY_PER_PIP_001,'modified':True,'reason':'C2_SHORT_HIGHVOL_EXTENSION_60S_ACCEPTANCE_FAIL'})
                        s['resolved']=True
                if all(s['resolved'] for s in states.values()):break
            if all(s['resolved'] for s in states.values()):break
        unresolved=[idx for idx,s in states.items() if not s['resolved']]
        if unresolved:raise RuntimeError(f'C2 60s unresolved {ym}: {len(unresolved)}')
    return out
def trade_metrics(rows:list[dict[str,Any]])->dict[str,Any]:
    r=sorted(rows,key=lambda x:(x['close_utc'],x['strategy'],x['trade_id']));vals=np.array([float(t['pnl_jpy']) for t in r]);gp=float(vals[vals>0].sum()) if len(vals) else 0;gl=float(vals[vals<0].sum()) if len(vals) else 0;eq=INITIAL_EQUITY;peak=eq;dd=0;mine=eq;streak=0;maxstreak=0;under_start=None;longest=pd.Timedelta(0)
    for t in r:
        eq+=t['pnl_jpy'];mine=min(mine,eq)
        if eq>=peak-1e-9:
            if under_start is not None:longest=max(longest,t['close_utc']-under_start);under_start=None
            peak=max(peak,eq)
        else:
            if under_start is None:under_start=t['close_utc']
            dd=max(dd,peak-eq)
        if t['pnl_jpy']<0:streak+=1;maxstreak=max(maxstreak,streak)
        elif t['pnl_jpy']>0:streak=0
    if under_start is not None and r:longest=max(longest,r[-1]['close_utc']-under_start)
    wins=sorted([v for v in vals if v>0],reverse=True)
    return {'trades':len(r),'net_jpy':float(vals.sum()),'gross_profit_jpy':gp,'gross_loss_jpy':gl,'profit_factor':gp/abs(gl) if gl<0 else None,'win_rate':float((vals>0).mean()) if len(vals) else None,'average_trade_jpy':float(vals.mean()) if len(vals) else None,'median_trade_jpy':float(np.median(vals)) if len(vals) else None,'realized_drawdown_jpy':dd,'minimum_realized_equity_jpy':mine,'maximum_consecutive_losses':maxstreak,'longest_realized_underwater_hours':longest.total_seconds()/3600,'top_1_winner_removal_net_jpy':float(vals.sum()-sum(wins[:1])),'top_3_winner_removal_net_jpy':float(vals.sum()-sum(wins[:3])),'top_5_winner_removal_net_jpy':float(vals.sum()-sum(wins[:5])),'modified_trades':sum(bool(t.get('modified')) for t in r)}
def period_tables(portfolios:dict[str,list[dict[str,Any]]])->dict[str,pd.DataFrame]:
    specs={'annual':lambda t:str(t['entry_utc'].year),'halfyear':lambda t:half_label(t['entry_utc']),'quarterly':lambda t:quarter_label(t['entry_utc']),'monthly':lambda t:t['entry_utc'].strftime('%Y-%m')};out={}
    for name,fn in specs.items():
        rows=[]
        for pid,trades in portfolios.items():
            groups=defaultdict(list)
            for t in trades:groups[fn(t)].append(t)
            for period,g in sorted(groups.items()):rows.append({'portfolio_id':pid,'period':period,**trade_metrics(g)})
        out[name]=pd.DataFrame(rows)
    return out
def full_equity(portfolios:dict[str,list[dict[str,Any]]],root:Path)->dict[str,Any]:
    results={pid:{'balance':INITIAL_EQUITY,'peak':INITIAL_EQUITY,'max_dd':0.0,'min_equity':INITIAL_EQUITY,'min_free_margin':INITIAL_EQUITY,'min_margin_level':None,'max_concurrency':0,'max_same_direction_concurrency':0,'max_opposite_direction_concurrency':0,'stopout_breached':False,'tick_count':0} for pid in portfolios};files=[]
    for ym,p in normalized_files(root).items():
        if '2020-01'<=ym<='2022-12':files.append((ym,p))
    for ym,p in sorted(files):
        d=pd.read_csv(p,compression='gzip',usecols=['timestamp_utc','bid','ask']);times=pd.to_datetime(d.timestamp_utc,utc=True);ns=times.astype('int64').to_numpy();bid=d.bid.to_numpy(float);ask=d.ask.to_numpy(float);n=len(d)
        if n==0:continue
        month_start=times.iloc[0];month_end=times.iloc[-1]
        for pid,trades in portfolios.items():
            r=results[pid];balance_delta=np.zeros(n+1);floating=np.zeros(n);long_delta=np.zeros(n+1,dtype=np.int32);short_delta=np.zeros(n+1,dtype=np.int32)
            for t in trades:
                if t['close_utc']<month_start or t['entry_utc']>month_end:continue
                lo=int(np.searchsorted(ns,int(t['entry_utc'].value),'left'));hi=int(np.searchsorted(ns,int(t['close_utc'].value),'left'));lo=max(0,min(n,lo));hi=max(0,min(n,hi))
                if month_start<=t['close_utc']<=month_end and hi<n:balance_delta[hi]+=t['pnl_jpy']
                if hi>lo:
                    if t['side']==1:floating[lo:hi]+=(bid[lo:hi]-t['entry_price'])/PIP*JPY_PER_PIP_001;long_delta[lo]+=1;long_delta[hi]-=1
                    else:floating[lo:hi]+=(t['entry_price']-ask[lo:hi])/PIP*JPY_PER_PIP_001;short_delta[lo]+=1;short_delta[hi]-=1
            realized=r['balance']+np.cumsum(balance_delta[:-1]);equity=realized+floating;longs=np.cumsum(long_delta[:-1]);shorts=np.cumsum(short_delta[:-1]);count=longs+shorts;margin=count*bid*(CONTRACT_SIZE*LOT/LEVERAGE);free=equity-margin;level=np.where(margin>0,equity/margin*100,np.inf);prefix=np.maximum.accumulate(np.r_[r['peak'],equity])[1:];dd=prefix-equity
            r['peak']=max(r['peak'],float(equity.max(initial=r['peak'])));r['max_dd']=max(r['max_dd'],float(dd.max(initial=0)));r['min_equity']=min(r['min_equity'],float(equity.min(initial=r['min_equity'])));r['min_free_margin']=min(r['min_free_margin'],float(free.min(initial=r['min_free_margin'])));finite=level[np.isfinite(level)]
            if len(finite):r['min_margin_level']=float(finite.min()) if r['min_margin_level'] is None else min(r['min_margin_level'],float(finite.min()))
            r['max_concurrency']=max(r['max_concurrency'],int(count.max(initial=0)));r['max_same_direction_concurrency']=max(r['max_same_direction_concurrency'],int(np.maximum(longs,shorts).max(initial=0)));r['max_opposite_direction_concurrency']=max(r['max_opposite_direction_concurrency'],int(np.minimum(longs,shorts).max(initial=0)));r['stopout_breached']=r['stopout_breached'] or bool(np.any((margin>0)&(level<STOPOUT_LEVEL)));r['tick_count']+=n;r['balance']=float(realized[-1])
    for r in results.values():
        r['ending_balance_jpy']=r.pop('balance');r['full_equity_drawdown_jpy']=r.pop('max_dd');r['minimum_equity_jpy']=r.pop('min_equity');r['minimum_free_margin_jpy']=r.pop('min_free_margin');r['minimum_margin_level_pct']=r.pop('min_margin_level');r['virtual_leverage']=LEVERAGE;r['virtual_stopout_level_pct']=STOPOUT_LEVEL
    return results
def main()->None:
    ap=argparse.ArgumentParser();ap.add_argument('--data-root',type=Path,required=True);ap.add_argument('--c2-summary',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    x=add_features(load_bars(args.data_root));b02,f05=generate_b02_f05(x);b02c3=apply_b02_c3(b02,x);c2sum=json.loads(args.c2_summary.read_text(encoding='utf-8'));thresholds=c2sum['f05_c2']['thresholds'];f05c2=assign_c2_tick_outcomes(f05,thresholds,args.data_root);sp=generate_sp(x)
    portfolios={'P0_B02_BASELINE_F05_BASELINE':[*b02,*f05],'P1_B02_BASELINE_F05_C2':[*b02,*f05c2],'P2_B02_C3_F05_BASELINE':[*b02c3,*f05],'P3_B02_C3_F05_C2':[*b02c3,*f05c2],'P4_B02_C3_F05_C2_SP39':[*b02c3,*f05c2,*sp]};variants={'B02_BASELINE':b02,'B02_C3':b02c3,'F05_BASELINE':f05,'F05_C2':f05c2,'SP39_UNCHANGED':sp};ledger=[]
    for vid,rows in variants.items():
        for t in rows:ledger.append({'variant_id':vid,**t})
    frame=pd.DataFrame(ledger)
    for c in frame.columns:
        if len(frame) and isinstance(frame[c].iloc[0],pd.Timestamp):frame[c]=frame[c].map(lambda z:z.isoformat() if pd.notna(z) else '')
    frame.to_csv(args.out/'source_native_trade_ledger_2020_2022.csv',index=False)
    for name,d in period_tables(portfolios).items():d.to_csv(args.out/f'{name}_metrics_2020_2022.csv',index=False)
    strategy={k:trade_metrics(v) for k,v in variants.items()};portfolio={k:trade_metrics(v) for k,v in portfolios.items()};fe=full_equity(portfolios,args.data_root)
    summary={'schema_version':'usdjpy_hyp044_source_native_2020_2022_result_v1','hypothesis_id':'USDJPY-HYP-044','status':'PASS_SOURCE_NATIVE_2020_2022_ANALYSIS','authority':'USDJPY-DATA-2020-2022-TICK-AUTHORITY-001','bar_rows':len(x),'bar_start':x.time.min(),'bar_end':x.time.max(),'c2_thresholds_from_2023_2024_authority':thresholds,'strategy_metrics':strategy,'portfolio_metrics':portfolio,'full_equity_metrics':fe,'counts':{k:len(v) for k,v in variants.items()},'period_role':'ANALYSIS_PERIOD','2025H2_accessed':False};write_json(args.out/'source_native_result_2020_2022.json',summary)
    with (args.out/'sha256sums.txt').open('w',encoding='utf-8') as f:
        for p in sorted(args.out.iterdir()):
            if p.is_file() and p.name!='sha256sums.txt':f.write(f'{sha256(p)}  {p.name}\n')
    print(json.dumps(clean({'status':summary['status'],'counts':summary['counts'],'portfolio_metrics':portfolio,'full_equity':fe}),indent=2))
if __name__=='__main__':main()

from __future__ import annotations
import hashlib, json, math, sys
from collections import defaultdict
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

FOLDS=["2023H1","2023H2","2024H1","2024H2"]
SCOPES=["ALL","B02","F05"]
STRATEGIES=["B02","F05"]
RNG_SEED=170125
PIP=0.01


def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''):h.update(c)
    return h.hexdigest()


def write_json(path:Path,obj:Any)->None:
    path.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False,default=lambda x:float(x) if isinstance(x,np.floating) else int(x) if isinstance(x,np.integer) else bool(x) if isinstance(x,np.bool_) else x.isoformat() if isinstance(x,pd.Timestamp) else str(x))+'\n')


def scope(df:pd.DataFrame,name:str)->pd.DataFrame:
    return df if name=='ALL' else df[df.strategy==name]


def verify_protocol(path:Path)->dict[str,Any]:
    p=json.loads(path.read_text())
    assert p['schema_version']=='usdjpy_b02_f05_structural_sl_policy_regime_protocol_v3'
    assert p['status']=='FROZEN_BEFORE_OUTCOME_EXECUTION'
    assert p['population']['trade_count']==1882 and p['population']['folds']==FOLDS
    assert p['authorization']['direct_user_instruction'] and not p['authorization']['notion_task_dependency']
    assert not p['boundaries']['fixed_pip_stop_evaluated'] and not p['boundaries']['mt4_accessed'] and not p['boundaries']['2025_accessed']
    assert not p['decision_boundary']['candidate_freeze_allowed']
    return p


def load_atlas(atlas_dir:Path,p:dict[str,Any])->tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    files={'atlas_event_ledger_sha256':atlas_dir/'deterministic_event_ledger_v2.csv.gz','atlas_metrics_sha256':atlas_dir/'deterministic_candidate_metrics_v2.csv','atlas_trajectory_sha256':atlas_dir/'trajectory_diagnostics_v2.csv'}
    for k,f in files.items():assert sha256_file(f)==p['source_authorities'][k],(k,sha256_file(f))
    e=pd.read_csv(files['atlas_event_ledger_sha256'],parse_dates=['entry_utc','trigger_utc','exit_utc'])
    for c in ['entry_utc','trigger_utc','exit_utc']:e[c]=pd.to_datetime(e[c],utc=True)
    m=pd.read_csv(files['atlas_metrics_sha256']);d=pd.read_csv(files['atlas_trajectory_sha256'])
    assert len(e)==354304 and m.candidate_id.nunique()==303 and len(d)==1882
    return e,m,d


def make_master(trades:pd.DataFrame,diag:pd.DataFrame)->pd.DataFrame:
    cols=['trade_id','fold','strategy','side','entry_utc','close_utc','baseline_pips','entry_price','breakout_level']
    dcols=['trade_id','scale_pips','pre_range_pips','session']
    x=trades[cols].merge(diag[dcols],on='trade_id',how='left',validate='one_to_one')
    x.entry_utc=pd.to_datetime(x.entry_utc,utc=True);x.close_utc=pd.to_datetime(x.close_utc,utc=True)
    x['month']=x.entry_utc.dt.strftime('%Y-%m');x['date']=x.entry_utc.dt.strftime('%Y-%m-%d');x['baseline_loser']=x.baseline_pips<=0
    assert len(x)==1882 and x.scale_pips.notna().all()
    return x


def train_candidate_metrics(g:pd.DataFrame)->tuple[bool,float,dict[str,float]]:
    if g.empty:return False,-1e30,{}
    lo=g[g.baseline_loser];wi=g[~g.baseline_loser]
    mo=g.assign(month=g.entry_utc.dt.strftime('%Y-%m')).groupby('month').delta_pips.sum()
    side=g.groupby('side').delta_pips.sum().reindex([1,-1],fill_value=0.)
    total=float(g.delta_pips.sum());sev=float(g.severe1_delta_pips.sum());delay=float(g.delay2_delta_pips.fillna(0).sum())
    benefit=float(lo.delta_pips.sum());damage=float(wi.delta_pips.sum());ex=total-(float(mo.max()) if len(mo) else 0.)
    ratio=float((mo>0).sum()/max(len(mo),1))
    ok=len(g)>=8 and len(lo)>=5 and total>0 and sev>0 and delay>0 and ex>0 and benefit>0 and damage>=-.7*benefit and ratio>=.55 and float(side.min())>=0
    return ok,min(total,sev,delay,ex,float(side.min())*2),{'total':total,'severe':sev,'delay':delay,'benefit':benefit,'damage':damage,'ex_best':ex,'ratio':ratio}


def select_candidate(events:pd.DataFrame,family:str|None=None)->tuple[str|None,dict[str,float]]:
    q=events if family is None else events[events.family==family]
    best=None
    for cid,g in q.groupby('candidate_id',sort=False):
        ok,score,d=train_candidate_metrics(g)
        if ok and (best is None or (score,str(cid))>(best[0],best[1])):best=(score,str(cid),d)
    return (None,{}) if best is None else (best[1],best[2])


def bootstrap_month_ci(rows:pd.DataFrame,months:list[str],reps:int=2000)->tuple[float,float]:
    v=rows.assign(month=rows.entry_utc.dt.strftime('%Y-%m')).groupby('month').delta_pips.sum().reindex(months,fill_value=0.).to_numpy(float)
    rng=np.random.default_rng(RNG_SEED+len(rows)+int(abs(v.sum())*10)%10000);idx=rng.integers(0,len(v),(reps,len(v)));z=v[idx].sum(1)
    return float(np.quantile(z,.025)),float(np.quantile(z,.975))


def policy_summary(rows:pd.DataFrame,master:pd.DataFrame,method:str,pid:str)->dict[str,Any]:
    if rows.empty:rows=pd.DataFrame(columns=['baseline_loser','delta_pips','severe1_delta_pips','severe2_delta_pips','delay5_delta_pips','fold','side','entry_utc'])
    lo=rows[rows.baseline_loser==True];wi=rows[rows.baseline_loser==False]
    f=rows.groupby('fold').delta_pips.sum().reindex(FOLDS,fill_value=0.);fs=rows.groupby('fold').severe1_delta_pips.sum().reindex(FOLDS,fill_value=0.);sd=rows.groupby('side').delta_pips.sum().reindex([1,-1],fill_value=0.)
    months=sorted(master.month.unique());mo=rows.assign(month=rows.entry_utc.dt.strftime('%Y-%m')).groupby('month').delta_pips.sum().reindex(months,fill_value=0.)
    total=float(rows.delta_pips.sum());sev=float(rows.severe1_delta_pips.sum());sev2=float(rows.severe2_delta_pips.sum());delay=float(rows.delay5_delta_pips.fillna(0).sum())
    ben=float(lo.delta_pips.sum());dam=float(wi.delta_pips.sum());ex=total-(float(mo.max()) if len(mo) else 0.);ratio=float((mo>0).sum()/max(int((mo!=0).sum()),1));ci=bootstrap_month_ci(rows,months)
    passed=len(rows)>=12 and total>0 and sev>0 and delay>0 and float(f.min())>=0 and float(fs.min())>=0 and float(sd.min())>=0 and ex>0 and ben>0 and dam>=-.6*ben and ratio>=.6 and ci[0]>0
    return {'method':method,'policy_id':pid,'triggers':len(rows),'losers_triggered':len(lo),'winners_triggered':len(wi),'loser_benefit_pips':round(ben,1),'winner_damage_pips':round(dam,1),'total_delta_pips':round(total,1),'severe1_delta_pips':round(sev,1),'severe2_delta_pips':round(sev2,1),'delay5_delta_pips':round(delay,1),'fold_delta_pips':{k:round(float(f[k]),1) for k in FOLDS},'fold_severe1_pips':{k:round(float(fs[k]),1) for k in FOLDS},'long_delta_pips':round(float(sd[1]),1),'short_delta_pips':round(float(sd[-1]),1),'active_months':int((mo!=0).sum()),'positive_active_month_ratio':round(ratio,6),'ex_best_month_delta_pips':round(ex,1),'month_bootstrap_ci95_pips':[round(ci[0],1),round(ci[1],1)],'binding_gate_pass':bool(passed)}


def state_ledger(trades:pd.DataFrame,m23:pd.DataFrame,m24:pd.DataFrame,atlas)->pd.DataFrame:
    bars={'2023':atlas.aggregate_bars(m23,5),'2024':atlas.aggregate_bars(m24,5)};out=[]
    for n,tr in enumerate(trades.itertuples(index=False),1):
        y='2023' if str(tr.fold).startswith('2023') else '2024';m1=m23 if y=='2023' else m24;c=atlas.pre_context(m1,pd.Timestamp(tr.entry_utc),int(tr.side));p=atlas.path_frame(bars[y],tr,5,c)
        if p.get('n',0)==0:continue
        ids=np.flatnonzero(p['completion']<=pd.Timestamp(tr.entry_utc)+pd.Timedelta(minutes=240));cross=0;prev=0
        for j,i in enumerate(ids,1):
            s=np.sign(p['level_dist'][i]);cross+=int(prev!=0 and s*prev<0);prev=s if s!=0 else prev;tm=pd.Timestamp(p['completion'][i]);ex=atlas.exit_pips(m1.loc[pd.Timestamp(tr.entry_utc):pd.Timestamp(tr.close_utc)],tr,tm,0)
            if ex is None:continue
            recent=p['ret'][max(0,i-4):i+1]
            out.append({'trade_id':tr.trade_id,'fold':tr.fold,'strategy':tr.strategy,'side':int(tr.side),'session':atlas.session_name(pd.Timestamp(tr.entry_utc)),'entry_utc':tr.entry_utc,'baseline_pips':float(tr.baseline_pips),'baseline_loser':int(float(tr.baseline_pips)<=0),'time_idx':j,'minutes':j*5,'trigger_utc':tm,'exit_pips':float(ex[1]),'delta_pips':float(ex[1]-tr.baseline_pips),'current_norm':float(p['ret'][i]/c['scale_pips']),'mfe_norm':float(p['mfe'][i]/c['scale_pips']),'mae_norm':float(p['mae'][i]/c['scale_pips']),'giveback_norm':float((p['mfe'][i]-p['ret'][i])/c['scale_pips']),'level_distance_norm':float(p['level_dist'][i]/c['scale_pips']),'underwater_fraction':float(np.mean(p['ret'][:i+1]<=0)),'crossings':cross,'slope_tstat':float(atlas.rolling_tstat(recent)),'delta_norm':float(p['delta'][i]/c['scale_pips']),'time_fraction':j/48,'pre_range_pips':float(c['pre_range_pips'])})
        if n%250==0:print(json.dumps({'state_progress':n,'rows':len(out)}),file=sys.stderr)
    x=pd.DataFrame(out);x.entry_utc=pd.to_datetime(x.entry_utc,utc=True);x.trigger_utc=pd.to_datetime(x.trigger_utc,utc=True);return x

class GaussianMarkov:
    def __init__(self,k:int):self.k=k
    def fit(self,X:np.ndarray,lengths:list[int]):
        self.g=GaussianMixture(n_components=self.k,covariance_type='diag',reg_covar=1e-4,n_init=10,max_iter=200,random_state=RNG_SEED).fit(X);lab=self.g.predict(X);st=np.ones(self.k);tr=np.ones((self.k,self.k));p=0
        for L in lengths:
            q=lab[p:p+L];p+=L
            if len(q):st[q[0]]+=1
            for a,b in zip(q[:-1],q[1:]):tr[a,b]+=1
        self.ls=np.log(st/st.sum());self.lt=np.log(tr/tr.sum(1,keepdims=True));return self
    def emit(self,X):
        o=np.empty((len(X),self.k));d=X.shape[1]
        for k in range(self.k):
            c=np.maximum(self.g.covariances_[k],1e-8);z=X-self.g.means_[k];o[:,k]=-.5*(d*np.log(2*np.pi)+np.log(c).sum()+(z*z/c).sum(1))
        return o
    def one(self,X):
        if not len(X):return np.empty(0,int)
        e=self.emit(X);dp=np.empty_like(e);bk=np.zeros_like(e,int);dp[0]=self.ls+e[0]
        for t in range(1,len(X)):
            z=dp[t-1][:,None]+self.lt;bk[t]=z.argmax(0);dp[t]=z[bk[t],np.arange(self.k)]+e[t]
        s=np.empty(len(X),int);s[-1]=dp[-1].argmax()
        for t in range(len(X)-2,-1,-1):s[t]=bk[t+1,s[t+1]]
        return s
    def predict(self,X,lengths):
        out=[];p=0
        for L in lengths:out.append(self.one(X[p:p+L]));p+=L
        return np.concatenate(out)

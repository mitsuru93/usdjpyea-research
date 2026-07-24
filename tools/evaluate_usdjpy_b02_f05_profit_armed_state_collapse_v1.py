#!/usr/bin/env python3
"""Frozen finite evaluator for B02/F05 profit-armed directional-state collapse.

The evaluator supports an outcome-free preflight. Scientific evaluation may be run
only after registry authorization. It consumes the exact independent reproduction
trade and M15-open state ledgers; it does not tune state thresholds.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd

COMPONENTS = ["mom4_dir_pips", "macd_hist_dir_pips", "price_ema20_dir_pips"]
FOLDS = ["2023H1", "2023H2", "2024H1", "2024H2"]
ARMS = {"P2": {"arm_pips": 0.0, "disarm_pips": 10.0, "target_class": "P2_MINOR_FAVORABLE_THEN_LOSS"},
        "P1": {"arm_pips": 10.0, "disarm_pips": None, "target_class": "P1_GIVEBACK_TO_LOSS"}}
EXPECTED = [
    (f"O_{arm}_Q{q}_R{r}", arm, q, r)
    for arm in ["P2", "P1"] for q in [2, 3] for r in [1, 2]
]

def file_sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def pf(values: pd.Series) -> float:
    gain=float(values[values>0].sum()); loss=float(-values[values<0].sum())
    return (math.inf if gain>0 else 0.0) if loss==0 else gain/loss

def load_inputs(trades_path: Path, states_path: Path) -> tuple[pd.DataFrame,pd.DataFrame]:
    t=pd.read_csv(trades_path); s=pd.read_csv(states_path)
    t['entry_utc']=pd.to_datetime(t.entry_utc,utc=True); t['close_utc']=pd.to_datetime(t.close_utc,utc=True)
    t['trade_id']=t['fold'].astype(str)+'|'+t['strategy'].astype(str)+'|'+t.entry_utc.astype(str)+'|'+t.side.astype(int).astype(str)
    s['observation_utc']=pd.to_datetime(s.observation_utc,utc=True)
    assert len(t)==1882 and t.trade_id.is_unique
    assert set(FOLDS)==set(t.fold.unique())
    assert set(t.trade_id)==set(s.trade_id.unique())
    assert not s.duplicated(['trade_id','observation_index']).any()
    assert s.groupby('trade_id').observation_index.apply(lambda x:x.is_monotonic_increasing).all()
    assert all(c in s for c in COMPONENTS)
    return t,s

def simulate_candidate(trades: pd.DataFrame, states: pd.DataFrame, arm: str, quorum: int, persistence: int) -> pd.DataFrame:
    cfg=ARMS[arm]; rows=[]
    state_by={k:g.sort_values('observation_index').reset_index(drop=True) for k,g in states.groupby('trade_id',sort=False)}
    for tr in trades.itertuples(index=False):
        g=state_by[tr.trade_id]
        arm_pos=None
        if arm=='P2':
            hit=g.index[(g.executable_pips>cfg['arm_pips']) & (g.executable_pips<cfg['disarm_pips'])]
        else:
            hit=g.index[g.executable_pips>=cfg['arm_pips']]
        if len(hit): arm_pos=int(hit[0])
        trigger_pos=None; run=0; disarmed=False
        if arm_pos is not None:
            for i in range(arm_pos+1,len(g)):
                row=g.iloc[i]
                if arm=='P2' and row.executable_pips>=cfg['disarm_pips']:
                    disarmed=True; break
                vals=[row[c] for c in COMPONENTS]
                collapse=sum(bool(pd.notna(v) and v<=0) for v in vals)>=quorum
                run=run+1 if collapse else 0
                if run>=persistence:
                    trigger_pos=i; break
        exec_pos=None
        if trigger_pos is not None and trigger_pos+1<len(g): exec_pos=trigger_pos+1
        changed=exec_pos is not None
        if changed:
            ex=g.iloc[exec_pos]; exit_bid=float(ex.bid_open); side=int(tr.side)
            gross_move=side*(exit_bid-float(tr.entry_bid))/0.01
            default_pips=gross_move-0.5
            severe_pips=gross_move-2.5
            exit_utc=ex.observation_utc
        else:
            default_pips=float(tr.realized_pl_jpy)/10.0
            severe_pips=default_pips-2.0
            exit_utc=tr.close_utc
        base_default=float(tr.realized_pl_jpy)/10.0; base_severe=base_default-2.0
        rows.append({
            'trade_id':tr.trade_id,'fold':tr.fold,'strategy':tr.strategy,'side':int(tr.side),'path_class':state_by[tr.trade_id].path_class.iloc[0],
            'arm':arm,'quorum':quorum,'persistence':persistence,'armed':arm_pos is not None,'disarmed_at_plus10':disarmed,
            'triggered':trigger_pos is not None,'changed':changed,'candidate_exit_utc':exit_utc,
            'baseline_default_pips':base_default,'baseline_severe_pips':base_severe,
            'candidate_default_pips':default_pips,'candidate_severe_pips':severe_pips,
            'default_delta_pips':default_pips-base_default,'severe_delta_pips':severe_pips-base_severe,
        })
    return pd.DataFrame(rows)

def fold_metrics(d: pd.DataFrame, candidate_id: str, arm: str) -> list[dict]:
    target=ARMS[arm]['target_class']; out=[]
    for fold in FOLDS:
        g=d[d.fold==fold].copy(); target_g=g[g.path_class==target]; winners=g[g.path_class=='WINNER']
        base=g.baseline_default_pips; cand=g.candidate_default_pips; csev=g.candidate_severe_pips
        dates=pd.to_datetime(g.candidate_exit_utc,utc=True).dt.strftime('%Y-%m-%d')
        months=pd.to_datetime(g.candidate_exit_utc,utc=True).dt.strftime('%Y-%m')
        quarters=pd.to_datetime(g.candidate_exit_utc,utc=True).dt.to_period('Q').astype(str)
        delta=g.default_delta_pips
        daily=delta.groupby(dates).sum(); monthly=delta.groupby(months).sum(); quarterly=delta.groupby(quarters).sum()
        target_benefit=float(target_g.default_delta_pips.sum()); winner_effect=float(winners.default_delta_pips.sum())
        top=winners[winners.baseline_default_pips>=winners.baseline_default_pips.quantile(.9)] if len(winners) else winners
        top_base=float(top.baseline_default_pips.sum()); top_cand=float(top.candidate_default_pips.sum()); retention=1.0 if top_base<=0 else top_cand/top_base
        strategy_effect=g.groupby('strategy').default_delta_pips.sum().to_dict(); direction_effect=g.groupby('side').default_delta_pips.sum().to_dict()
        candidate_default=float(cand.sum()); candidate_severe=float(csev.sum())
        core=(candidate_default>0 and pf(cand)>=1 and candidate_severe>0 and pf(csev)>=1 and
              target_benefit>0 and int(target_g.changed.sum())>=5 and retention>=.90 and
              all(strategy_effect.get(x,0)>=0 for x in ['B02','F05']) and
              all(direction_effect.get(x,0)>=0 for x in [-1,1]) and
              len(quarterly)>=2 and bool((quarterly>=0).all()))
        ex2=float(delta.sum()-daily.sort_values(ascending=False).head(2).sum())
        full=core and int((monthly>0).sum())>=4 and int((monthly<0).sum())<=2 and ex2>0
        out.append({'candidate_id':candidate_id,'arm':arm,'fold':fold,'trades':len(g),'changed':int(g.changed.sum()),'target_changed':int(target_g.changed.sum()),
                    'baseline_default_net_pips':float(base.sum()),'candidate_default_net_pips':candidate_default,'candidate_default_pf':pf(cand),
                    'candidate_severe_net_pips':candidate_severe,'candidate_severe_pf':pf(csev),'default_delta_pips':float(delta.sum()),
                    'target_class_benefit_pips':target_benefit,'winner_effect_pips':winner_effect,'top_decile_winner_retention':retention,
                    'B02_delta_pips':float(strategy_effect.get('B02',0)),'F05_delta_pips':float(strategy_effect.get('F05',0)),
                    'long_delta_pips':float(direction_effect.get(1,0)),'short_delta_pips':float(direction_effect.get(-1,0)),
                    'minimum_quarter_delta_pips':float(quarterly.min()) if len(quarterly) else 0.0,'positive_effect_months':int((monthly>0).sum()),
                    'negative_effect_months':int((monthly<0).sum()),'ex_best_two_dates_delta_pips':ex2,'core_pass':bool(core),'full_pass':bool(full)})
    return out

def family_region(cells: pd.DataFrame, arm: str) -> dict:
    a=cells[cells.arm==arm].copy(); coords={(int(r.quorum),int(r.persistence)):r.candidate_id for r in a.itertuples() if r.core_all_folds}; comps=[];seen=set()
    for node in coords:
        if node in seen: continue
        stack=[node];seen.add(node);comp=[]
        while stack:
            cur=stack.pop();comp.append(coords[cur])
            for nb in [(cur[0]-1,cur[1]),(cur[0]+1,cur[1]),(cur[0],cur[1]-1),(cur[0],cur[1]+1)]:
                if nb in coords and nb not in seen: seen.add(nb);stack.append(nb)
        comps.append(sorted(comp))
    full=set(a.loc[a.full_all_folds,'candidate_id']); eligible=sorted({x for c in comps if len(c)>=2 and full.intersection(c) for x in c})
    return {'arm':arm,'components':comps,'eligible_candidates':eligible}

def main() -> None:
    ap=argparse.ArgumentParser();ap.add_argument('--trades',type=Path,required=True);ap.add_argument('--states',type=Path,required=True);ap.add_argument('--protocol',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);ap.add_argument('--preflight-only',action='store_true');a=ap.parse_args()
    protocol=json.loads(a.protocol.read_text()); assert protocol['candidate_ids']==[x[0] for x in EXPECTED] and protocol['status']=='FROZEN_BEFORE_CANDIDATE_OUTCOME_EVALUATION'
    trades,states=load_inputs(a.trades,a.states); a.output_dir.mkdir(parents=True,exist_ok=True)
    pre={'schema_version':'usdjpy_b02_f05_profit_armed_state_collapse_preflight_v1','status':'PASS','candidate_count':len(EXPECTED),'trade_rows':len(trades),'state_rows':len(states),'trade_id_count':states.trade_id.nunique(),'protocol_sha256':file_sha(a.protocol),'evaluator_sha256':file_sha(Path(__file__)),'trades_sha256':file_sha(a.trades),'states_sha256':file_sha(a.states),'outcomes_computed':not a.preflight_only}
    (a.output_dir/'usdjpy_b02_f05_profit_armed_state_collapse_preflight_v1.json').write_text(json.dumps(pre,indent=2,sort_keys=True)+'\n')
    if a.preflight_only: print(json.dumps(pre,indent=2,sort_keys=True)); return
    trade_frames=[]; metric_rows=[]; cell_rows=[]
    for cid,arm,q,p in EXPECTED:
        d=simulate_candidate(trades,states,arm,q,p); d.insert(0,'candidate_id',cid); trade_frames.append(d)
        fm=fold_metrics(d,cid,arm); metric_rows.extend(fm); cell_rows.append({'candidate_id':cid,'arm':arm,'quorum':q,'persistence':p,'core_all_folds':all(x['core_pass'] for x in fm),'full_all_folds':all(x['full_pass'] for x in fm),'minimum_fold_default_delta_pips':min(x['default_delta_pips'] for x in fm),'minimum_fold_target_benefit_pips':min(x['target_class_benefit_pips'] for x in fm),'minimum_top_decile_winner_retention':min(x['top_decile_winner_retention'] for x in fm)})
    alltr=pd.concat(trade_frames,ignore_index=True); fm=pd.DataFrame(metric_rows); cells=pd.DataFrame(cell_rows); regions=[family_region(cells,a) for a in ['P2','P1']]
    eligible=sorted({x for r in regions for x in r['eligible_candidates']}); finalist=None
    if eligible:
        finalist=str(cells[cells.candidate_id.isin(eligible)].sort_values(['minimum_fold_default_delta_pips','minimum_fold_target_benefit_pips','minimum_top_decile_winner_retention'],ascending=False).iloc[0].candidate_id)
    alltr.to_csv(a.output_dir/'usdjpy_b02_f05_profit_armed_state_collapse_trades_v1.csv.gz',index=False,compression={'method':'gzip','mtime':0},lineterminator='\n')
    fm.to_csv(a.output_dir/'usdjpy_b02_f05_profit_armed_state_collapse_fold_metrics_v1.csv',index=False,lineterminator='\n')
    cells.to_csv(a.output_dir/'usdjpy_b02_f05_profit_armed_state_collapse_cell_summary_v1.csv',index=False,lineterminator='\n')
    result={'schema_version':'usdjpy_b02_f05_profit_armed_state_collapse_result_v1','status':'ELIGIBLE_FAMILY_REGION' if finalist else 'CLOSED_NO_ELIGIBLE_FAMILY_REGION','candidate_count':len(EXPECTED),'core_cells':int(cells.core_all_folds.sum()),'full_cells':int(cells.full_all_folds.sum()),'family_regions':regions,'eligible_candidates':eligible,'finalist':finalist,'cells':cells.to_dict('records'),'boundaries':{'2025_accessed':False,'MT4_accessed':False,'grid_expanded':False,'gate_changed':False}}
    result['output_sha256']={p.name:file_sha(p) for p in a.output_dir.iterdir() if p.is_file() and p.name!='usdjpy_b02_f05_profit_armed_state_collapse_result_v1.json'}
    (a.output_dir/'usdjpy_b02_f05_profit_armed_state_collapse_result_v1.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__': main()

#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from usdjpy_native_htf_state_data_v1 import load_m15_2023, load_m15_2024, aggregate_exact, add_state

FOLDS=["2023H1","2023H2","2024H1","2024H2"]
RULES=["H1_ALIGNED","H4_ALIGNED","BOTH_ALIGNED","H1_ALIGNED_H4_NOT_OPPOSED","H4_ALIGNED_H1_NOT_OPPOSED"]
CELLS=[("S1",3,12,4,16),("S2",3,12,8,32),("S3",6,24,4,16),("S4",6,24,8,32),("S5",12,48,4,16),("S6",12,48,8,32)]
EXPECTED_TRADE_SHA="98c9c8cf57c62c23a94aa38efa6ee257e823dd0b68c413615197a48be00b08ca"

def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()

def permission(rule:str,side:pd.Series,h1:pd.Series,h4:pd.Series)->pd.Series:
 a=h1.eq(side);b=h4.eq(side);h1opp=h1.eq(-side);h4opp=h4.eq(-side)
 if rule=="H1_ALIGNED":return a
 if rule=="H4_ALIGNED":return b
 if rule=="BOTH_ALIGNED":return a&b
 if rule=="H1_ALIGNED_H4_NOT_OPPOSED":return a&~h4opp
 if rule=="H4_ALIGNED_H1_NOT_OPPOSED":return b&~h1opp
 raise ValueError(rule)

def join_latest(trades:pd.DataFrame,state:pd.DataFrame,col:str)->pd.Series:
 left=trades[["_row","entry_utc"]].sort_values("entry_utc")
 right=state[["information_utc",col]].sort_values("information_utc")
 out=pd.merge_asof(left,right,left_on="entry_utc",right_on="information_utc",direction="backward",allow_exact_matches=True)
 return out.set_index("_row")[col].reindex(trades._row).fillna(0).astype(int).reset_index(drop=True)

def metrics(x:pd.DataFrame,allow:pd.Series)->dict:
 blocked=x[~allow].copy();delta=-blocked.realized_pl_jpy.astype(float)
 loser=blocked.realized_pl_jpy.le(0);winner=blocked.realized_pl_jpy.gt(0)
 return {"trades":len(x),"blocked":len(blocked),"loser_benefit_jpy":float(delta[loser].sum()),"winner_damage_jpy":float(-delta[winner].sum()),"net_delta_jpy":float(delta.sum())}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--trades',type=Path,required=True);ap.add_argument('--m15-2023',type=Path,required=True);ap.add_argument('--m15-2024',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);ap.add_argument('--research-sha',default='');ap.add_argument('--run-id',default='');a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 assert sha(a.trades)==EXPECTED_TRADE_SHA,(sha(a.trades),EXPECTED_TRADE_SHA)
 t=pd.read_csv(a.trades);t['entry_utc']=pd.to_datetime(t.entry_utc,utc=True);t['_row']=np.arange(len(t));assert len(t)==1882
 m=pd.concat([load_m15_2023(a.m15_2023),load_m15_2024(a.m15_2024)],ignore_index=True).sort_values('logical_utc').reset_index(drop=True)
 h1base=aggregate_exact(m,'1h',4);h4base=aggregate_exact(m,'4h',16)
 grid=[];trade_rows=[]
 for cid,h4f,h4s,h1f,h1s in CELLS:
  h1=add_state(h1base,h1f,h1s,'h1');h4=add_state(h4base,h4f,h4s,'h4')
  h1srs=join_latest(t,h1,'h1_state');h4srs=join_latest(t,h4,'h4_state')
  for rule in RULES:
   rid=f"{cid}_{rule}";allow=permission(rule,t.side.astype(int),h1srs,h4srs)
   for fold in FOLDS:
    idx=t.fold.eq(fold);r=metrics(t[idx],allow[idx]);grid.append({"rule_id":rid,"cell":cid,"rule":rule,"fold":fold,**r})
   for strat in ['B02','F05']:
    for fold in FOLDS:
     idx=t.fold.eq(fold)&t.strategy.eq(strat);r=metrics(t[idx],allow[idx]);grid.append({"rule_id":rid,"cell":cid,"rule":rule,"fold":fold,"strategy":strat,**r})
   changed=t[~allow].copy();changed['rule_id']=rid;changed['h1_state']=h1srs[~allow].to_numpy();changed['h4_state']=h4srs[~allow].to_numpy();changed['delta_jpy']=-changed.realized_pl_jpy;trade_rows.append(changed[['rule_id','fold','strategy','side','entry_utc','realized_pl_jpy','h1_state','h4_state','delta_jpy']])
 g=pd.DataFrame(grid);pooled=g[g['strategy'].isna()].copy();foldmat=pooled.pivot(index='rule_id',columns='fold',values='net_delta_jpy')
 summaries=[]
 for rid,row in foldmat.iterrows():
  q=pooled[pooled.rule_id.eq(rid)];summaries.append({"rule_id":rid,"min_fold_net_jpy":float(row.min()),"pooled_net_jpy":float(row.sum()),"positive_folds":int((row>0).sum()),"blocked":int(q.blocked.sum()),"winner_damage_jpy":float(q.winner_damage_jpy.sum()),"loser_benefit_jpy":float(q.loser_benefit_jpy.sum())})
 s=pd.DataFrame(summaries).sort_values(['min_fold_net_jpy','pooled_net_jpy','winner_damage_jpy','blocked','rule_id'],ascending=[False,False,True,True,True],kind='mergesort').reset_index(drop=True);s.insert(0,'descriptive_rank',np.arange(1,len(s)+1))
 lofo=[]
 for held in FOLDS:
  train=[f for f in FOLDS if f!=held];cand=[]
  for rid in foldmat.index:
   q=foldmat.loc[rid,train];meta=s[s.rule_id.eq(rid)].iloc[0];cand.append({"rule_id":rid,"min_train":float(q.min()),"pooled_train":float(q.sum()),"winner_damage":float(meta.winner_damage_jpy),"blocked":int(meta.blocked)})
  c=pd.DataFrame(cand).sort_values(['min_train','pooled_train','winner_damage','blocked','rule_id'],ascending=[False,False,True,True,True],kind='mergesort').iloc[0];rid=str(c.rule_id)
  heldrow=pooled[(pooled.rule_id.eq(rid))&(pooled.fold.eq(held))].iloc[0]
  rec={"held_out_fold":held,"selected_rule_id":rid,"held_out_net_delta_jpy":float(heldrow.net_delta_jpy),"held_out_blocked":int(heldrow.blocked)}
  for strat in ['B02','F05']:
   z=g[(g.rule_id.eq(rid))&(g.fold.eq(held))&(g.strategy.eq(strat))].iloc[0];rec[f"{strat}_net_delta_jpy"]=float(z.net_delta_jpy)
  lofo.append(rec)
 l=pd.DataFrame(lofo);positive=int((l.held_out_net_delta_jpy>0).sum());breadth={x:int((l[f'{x}_net_delta_jpy']>=0).sum()) for x in ['B02','F05']};support=bool((l.held_out_blocked>=5).all());portable=positive>=3 and min(breadth.values())>=3 and support
 status='PASS_PORTABLE_MARKET_STATE_ROUTER' if portable else 'FAIL_NO_PORTABLE_MARKET_STATE_ROUTER'
 g.to_csv(a.out_dir/'market_state_rule_fold_strategy_metrics.csv',index=False);s.to_csv(a.out_dir/'market_state_rule_summary.csv',index=False);l.to_csv(a.out_dir/'market_state_lofo.csv',index=False);pd.concat(trade_rows,ignore_index=True).to_csv(a.out_dir/'market_state_blocked_trade_ledger.csv.gz',index=False,compression='gzip')
 result={"status":status,"population":{"trades":len(t)},"rules":len(s),"lofo_positive_folds":positive,"strategy_nonnegative_folds":breadth,"support_gate":support,"portable":portable,"descriptive_best":s.iloc[0].to_dict(),"2025_accessed":False,"mt4_accessed":False,"candidate_authorized":False,"research_sha":a.research_sha,"run_id":a.run_id}
 def clean(v):return v.item() if hasattr(v,'item') else v
 result={k:clean(v) for k,v in result.items()};result['descriptive_best']={k:clean(v) for k,v in result['descriptive_best'].items()}
 (a.out_dir/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
 receipt={**result,"diagnostic_status":result['status'],"status":"PHASE2_DIAGNOSIS_COMPLETE_NO_CANDIDATE_AUTHORIZATION"}
 (a.out_dir/'execution_receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False,allow_nan=False)+'\n');print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=='__main__':main()

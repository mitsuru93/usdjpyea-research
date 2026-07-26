#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

FOLDS=["2023H1","2023H2","2024H1","2024H2"]
EXPECTED_TRADES="98c9c8cf57c62c23a94aa38efa6ee257e823dd0b68c413615197a48be00b08ca"
EXPECTED_STATES="2caddc38cdb16ce7504fe1e3b625f8425ccc6f7d579d02590f9ee92bbf013eda"

def sha256_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()

def load(trades_path:Path,states_path:Path):
 assert sha256_file(trades_path)==EXPECTED_TRADES
 assert sha256_file(states_path)==EXPECTED_STATES
 t=pd.read_csv(trades_path)
 s=pd.read_csv(states_path)
 assert len(t)==1882 and len(s)==68955 and s.trade_id.nunique()==1882
 for c in ['signal_utc','entry_utc','close_utc']: t[c]=pd.to_datetime(t[c],utc=True)
 s['observation_utc']=pd.to_datetime(s.observation_utc,utc=True)
 if 'trade_id' not in t:
  t['trade_id']=t.apply(lambda r:f"{r['fold']}|{r['strategy']}|{pd.Timestamp(r['entry_utc'])}|{int(r['side'])}",axis=1)
 return t,s

def checkpoint_table(t,s,minute):
 idx=minute//15
 g=s[s.observation_index<=idx].copy()
 agg=g.groupby('trade_id',sort=False).agg(
  checkpoint_index=('observation_index','max'),
  checkpoint_utc=('observation_utc','max'),
  checkpoint_pips=('executable_pips','last'),
  checkpoint_mfe_pips=('executable_pips','max'),
  checkpoint_mae_pips=('executable_pips','min'),
  mom4=('mom4_dir_pips','last'),macd=('macd_hist_dir_pips','last'),ema=('price_ema20_dir_pips','last'))
 out=t.merge(agg,on='trade_id',how='left',validate='one_to_one')
 out=out[out.checkpoint_index.eq(idx)].copy()
 out['checkpoint_close_jpy']=(out.checkpoint_pips*10).round()
 out['delta_jpy']=out.checkpoint_close_jpy-out.realized_pl_jpy
 out['winner']=out.realized_pl_jpy.gt(0)
 out['positive_votes']=(out.checkpoint_pips.gt(0).astype(int)+out.mom4.gt(0).astype(int)+out.macd.gt(0).astype(int)+out.ema.gt(0).astype(int))
 return out

def candidates():
 rows=[]
 for m in [15,30,45,60]:
  for x in [0.,1.,2.,3.]: rows.append(dict(family='non_expansion',minute=m,p1=x,p2=np.nan,label=f'NE_m{m}_mfe_lt_{x:g}'))
  for mae in [3.,5.,7.,10.]:
   for rec in [0.,1.,2.]: rows.append(dict(family='adverse_first',minute=m,p1=mae,p2=rec,label=f'AF_m{m}_mae_ge_{mae:g}_mfe_lt_{rec:g}'))
  for votes in [1,2,3]: rows.append(dict(family='directional_confirmation',minute=m,p1=votes,p2=np.nan,label=f'DC_m{m}_votes_lt_{votes}'))
  for est in [2.,3.,5.]: rows.append(dict(family='signal_expiration',minute=m,p1=est,p2=np.nan,label=f'SE_m{m}_mfe_lt_{est:g}'))
 return pd.DataFrame(rows)

def fire(df,r):
 if r.family=='non_expansion': return df.checkpoint_mfe_pips.lt(r.p1)
 if r.family=='adverse_first': return df.checkpoint_mae_pips.le(-r.p1)&df.checkpoint_mfe_pips.lt(r.p2)
 if r.family=='directional_confirmation': return df.positive_votes.lt(int(r.p1))
 return df.checkpoint_mfe_pips.lt(r.p1)

def summarize(sub,mask):
 x=sub[mask]
 base_loss=(-x.loc[x.realized_pl_jpy<0,'realized_pl_jpy']).sum()
 loser_gain=x.loc[x.realized_pl_jpy<0,'delta_jpy'].sum()
 winner_damage=(-x.loc[x.realized_pl_jpy>0,'delta_jpy'].clip(upper=0)).sum()
 return dict(triggered=int(len(x)),losers=int((x.realized_pl_jpy<0).sum()),winners=int((x.realized_pl_jpy>0).sum()),net_delta_jpy=float(x.delta_jpy.sum()),gross_loss_avoided_jpy=float(max(loser_gain,0)),winner_damage_jpy=float(winner_damage),winner_damage_ratio=float(winner_damage/max(base_loss,1)),loser_capture_rate=float((x.realized_pl_jpy<0).sum()/max((sub.realized_pl_jpy<0).sum(),1)),winner_hit_rate=float((x.realized_pl_jpy>0).sum()/max((sub.realized_pl_jpy>0).sum(),1)))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--trades',type=Path,required=True);ap.add_argument('--states',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);ap.add_argument('--research-sha',default='LOCAL');ap.add_argument('--core-sha',default='aca45ab891d9a6da272b5111a99142d99e874929');ap.add_argument('--run-id',default='LOCAL');a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 t,s=load(a.trades,a.states); cps={m:checkpoint_table(t,s,m) for m in [15,30,45,60]}; cand=candidates(); detail=[]
 for r in cand.itertuples(index=False):
  d=cps[r.minute]; mask=fire(d,r)
  for fold in ['ALL']+FOLDS:
   sub=d if fold=='ALL' else d[d.fold==fold]; sm=summarize(sub,mask.loc[sub.index]);detail.append({'candidate':r.label,'family':r.family,'minute':r.minute,'p1':r.p1,'p2':r.p2,'fold':fold,**sm})
 detail=pd.DataFrame(detail);detail.to_csv(a.out_dir/'candidate_fold_metrics.csv',index=False)
 lofo=[]
 for held in FOLDS:
  train=[f for f in FOLDS if f!=held]; q=detail[detail.fold.isin(train)].groupby(['candidate','family','minute','p1','p2'],dropna=False,as_index=False).agg(triggered=('triggered','sum'),net_delta_jpy=('net_delta_jpy','sum'),gross_loss_avoided_jpy=('gross_loss_avoided_jpy','sum'),winner_damage_jpy=('winner_damage_jpy','sum'))
  q['winner_damage_ratio']=q.winner_damage_jpy/q.gross_loss_avoided_jpy.clip(lower=1)
  eligible=q[(q.triggered>=30)&(q.winner_damage_ratio<=.35)].sort_values(['net_delta_jpy','winner_damage_jpy','triggered'],ascending=[False,True,False])
  pick=(eligible.iloc[0] if len(eligible) else q.sort_values('net_delta_jpy',ascending=False).iloc[0]); test=detail[(detail.candidate==pick.candidate)&(detail.fold==held)].iloc[0]
  lofo.append({'held_out_fold':held,'selected_candidate':pick.candidate,'family':pick.family,'train_net_delta_jpy':float(pick.net_delta_jpy),'train_triggered':int(pick.triggered),'train_winner_damage_ratio':float(pick.winner_damage_ratio),'held_out_net_delta_jpy':float(test.net_delta_jpy),'held_out_triggered':int(test.triggered),'held_out_winner_damage_jpy':float(test.winner_damage_jpy),'held_out_gross_loss_avoided_jpy':float(test.gross_loss_avoided_jpy)})
 lofo=pd.DataFrame(lofo);lofo.to_csv(a.out_dir/'lofo_selection_results.csv',index=False)
 allm=detail[detail.fold=='ALL'].sort_values(['net_delta_jpy','winner_damage_jpy'],ascending=[False,True]);allm.to_csv(a.out_dir/'candidate_overall_ranking.csv',index=False)
 held_positive=int((lofo.held_out_net_delta_jpy>0).sum());best=allm.iloc[0]
 status='PHASE2_DIAGNOSIS_COMPLETE_NO_CANDIDATE_AUTHORIZATION'
 receipt={'schema_version':'usdjpy_entry_establishment_phase2_v1_receipt','status':status,'research_sha':a.research_sha,'core_sha':a.core_sha,'run_id':str(a.run_id),'population':{'trades':len(t),'states':len(s)},'2025_accessed':False,'mt4_accessed':False,'candidate_authorized':False,'production_authorized':False,'lofo':{'positive_held_out_folds':held_positive,'held_out_net_delta_jpy':lofo[['held_out_fold','held_out_net_delta_jpy']].to_dict('records')},'descriptive_best':{'candidate':best.candidate,'family':best.family,'net_delta_jpy':float(best.net_delta_jpy),'winner_damage_jpy':float(best.winner_damage_jpy),'triggered':int(best.triggered)},'gate_interpretation':'portable_signal' if held_positive>=3 else 'insufficient_portability'}
 (a.out_dir/'execution_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 report=f"# USDJPY Entry Establishment Phase 2 v1\n\nStatus: `{status}`\n\n- canonical trades: {len(t):,}\n- canonical state rows: {len(s):,}\n- LOFO positive held-out folds: {held_positive}/4\n- descriptive best: `{best.candidate}`\n- descriptive net delta: ¥{best.net_delta_jpy:,.0f}\n- winner damage: ¥{best.winner_damage_jpy:,.0f}\n- interpretation: `{receipt['gate_interpretation']}`\n\nNo 2025 data, MT4 execution, candidate authorization, EA implementation or production authorization was used.\n"
 (a.out_dir/'result_report.md').write_text(report,encoding='utf-8')
 print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__': main()

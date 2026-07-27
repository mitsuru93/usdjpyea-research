#!/usr/bin/env python3
import argparse, json
from pathlib import Path
import pandas as pd

ap=argparse.ArgumentParser()
ap.add_argument('--dev-lifecycle',type=Path,required=True)
ap.add_argument('--postmortem-2025-lifecycle',type=Path,required=True)
ap.add_argument('--final-decision',type=Path,required=True)
ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args()
decision=json.loads(a.final_decision.read_text())
assert decision['2025_used_for_selection'] is False

def summarize(period: str, df: pd.DataFrame) -> list[dict]:
    if period == 'CONSUMED_POSTMORTEM_2025':
        if 'fold' not in df.columns:
            raise ValueError('2025 comparison input requires fold column for period isolation')
        df=df[df['fold'].astype(str).isin(['2025H1','2025H2'])].copy()
        if df.empty:
            raise ValueError('2025H1/H2 rows missing from postmortem comparison input')
    if 'failure_class' in df.columns and 'lifecycle_class' not in df.columns:
        df=df.rename(columns={'failure_class':'lifecycle_class'})
    if 'lifecycle_class' not in df.columns:
        raise ValueError(f'{period}: lifecycle class column missing')
    rows=[]
    if {'trades','net_jpy'}.issubset(df.columns):
        grouped=(df.groupby('lifecycle_class',dropna=False)
                   .agg(events=('trades','sum'),net_jpy=('net_jpy','sum'))
                   .reset_index())
        total=float(grouped.events.sum())
        for r in grouped.itertuples(index=False):
            rows.append({'period_role':period,'lifecycle_class':r.lifecycle_class,'events':int(r.events),'share':float(r.events/total) if total else 0.0,'net_jpy':float(r.net_jpy)})
        return rows
    pnl_col='realized_pnl_jpy' if 'realized_pnl_jpy' in df.columns else 'pnl_jpy'
    if pnl_col not in df.columns:
        raise ValueError(f'{period}: event-level P/L column missing')
    total=float(len(df))
    for cls,g in df.groupby('lifecycle_class',dropna=False):
        rows.append({'period_role':period,'lifecycle_class':cls,'events':int(len(g)),'share':float(len(g)/total) if total else 0.0,'net_jpy':float(pd.to_numeric(g[pnl_col],errors='coerce').sum())})
    return rows

dev=pd.read_csv(a.dev_lifecycle,compression='infer')
y25=pd.read_csv(a.postmortem_2025_lifecycle)
rows=summarize('DEVELOPMENT_2023_2024',dev)+summarize('CONSUMED_POSTMORTEM_2025',y25)
out=pd.DataFrame(rows)
assert int(out.loc[out.period_role=='CONSUMED_POSTMORTEM_2025','events'].sum()) == 47
out.to_csv(a.out,index=False)
receipt={
  'schema_version':'usdjpy_shock_failure_regime_discriminator_2025_comparison_v1',
  'selection_completed_before_2025_comparison':True,
  'selection_status':decision['status'],
  'selected_candidate_id':decision.get('selected_candidate_id'),
  '2025_role':'CONSUMED_POSTMORTEM_COMPARISON_ONLY',
  '2025_folds_included':['2025H1','2025H2'],
  '2025_event_count':47,
  '2025_used_for_feature_threshold_model_or_rule_selection':False,
  'comparison_input_supports_event_or_aggregate_lifecycle':True
}
a.out.with_suffix('.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

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
dev=pd.read_csv(a.dev_lifecycle,compression='infer')
y25=pd.read_csv(a.postmortem_2025_lifecycle)
if 'failure_class' in y25.columns:
    y25=y25.rename(columns={'failure_class':'lifecycle_class'})
rows=[]
for period,df in [('DEVELOPMENT_2023_2024',dev),('CONSUMED_POSTMORTEM_2025',y25)]:
    for cls,g in df.groupby('lifecycle_class',dropna=False):
        pnl_col='realized_pnl_jpy' if 'realized_pnl_jpy' in g.columns else 'pnl_jpy'
        rows.append({'period_role':period,'lifecycle_class':cls,'events':len(g),'share':len(g)/len(df),'net_jpy':pd.to_numeric(g[pnl_col],errors='coerce').sum()})
out=pd.DataFrame(rows)
out.to_csv(a.out,index=False)
receipt={
  'schema_version':'usdjpy_shock_failure_regime_discriminator_2025_comparison_v1',
  'selection_completed_before_2025_comparison':True,
  'selection_status':decision['status'],
  'selected_candidate_id':decision.get('selected_candidate_id'),
  '2025_role':'CONSUMED_POSTMORTEM_COMPARISON_ONLY',
  '2025_used_for_feature_threshold_model_or_rule_selection':False
}
a.out.with_suffix('.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

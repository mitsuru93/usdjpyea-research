#!/usr/bin/env python3
"""Technical repair for the HYP-035 source-population precondition.

The original evaluator accidentally required more than 60,000 M15 bars for two
calendar years. A 24x5 USDJPY market has approximately 49,900 observed M15 bars.
This script changes only the undocumented population sanity threshold to the
pre-verified inclusive range 49,000..50,100. It does not change the Atlas rule,
event generation, Bid/Ask execution, P/L, any user-preregistered scientific gate,
period access, candidate, side, session, threshold, or hold time.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

REPLACEMENTS = {
    "r['m15_bar_count']>60000": "49000<=r['m15_bar_count']<=50100",
    "src['m15_bar_count']>60000": "49000<=src['m15_bar_count']<=50100",
}

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--evaluator', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    before_sha = digest(args.evaluator)
    text = args.evaluator.read_text(encoding='utf-8')
    counts = {}
    for old, new in REPLACEMENTS.items():
        count = text.count(old)
        counts[old] = count
        if count != 1:
            raise RuntimeError(f'expected exactly one occurrence of {old!r}, found {count}')
        text = text.replace(old, new)
    args.evaluator.write_text(text, encoding='utf-8')
    after_sha = digest(args.evaluator)
    receipt = {
        'schema_version': 'usdjpy_hyp035_source_population_repair_v1',
        'status': 'PASS_TECHNICAL_FALSE_GATE_REPAIR',
        'reason': 'Replace undocumented >60000 M15 population precondition with inclusive 49000..50100 range for 2023-2024 observed USDJPY M15 market bars.',
        'before_sha256': before_sha,
        'after_sha256': after_sha,
        'replacement_counts': counts,
        'candidate_changed': False,
        'atlas_rule_changed': False,
        'execution_semantics_changed': False,
        'scientific_gate_changed': False,
        'period_changed': False,
        'protected_2020_2022_accessed': False,
        'protected_2025_accessed': False,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()

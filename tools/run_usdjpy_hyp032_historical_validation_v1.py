#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime
import evaluate_usdjpy_hyp032_historical_validation_v1 as evaluator

def parse_native_timestamp(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.strptime(value, '%Y.%m.%d %H:%M:%S')

evaluator.dt = parse_native_timestamp

if __name__ == '__main__':
    evaluator.main()

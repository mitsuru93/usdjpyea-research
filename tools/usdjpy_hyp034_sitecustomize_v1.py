"""HYP-034 runtime JSON compatibility for the frozen NumPy/Pandas stack.

Loaded as sitecustomize.py inside the exact-SHA short work root. It changes only
JSON serialization of NumPy scalar values used in technical/scientific receipts.
No market data, event, candidate, threshold, P/L, or gate calculation is changed.
"""
from __future__ import annotations

import json

import numpy as np

_ORIGINAL_DEFAULT = json.JSONEncoder.default


def _numpy_scalar_default(self: json.JSONEncoder, value: object):
    if isinstance(value, np.generic):
        return value.item()
    return _ORIGINAL_DEFAULT(self, value)


json.JSONEncoder.default = _numpy_scalar_default

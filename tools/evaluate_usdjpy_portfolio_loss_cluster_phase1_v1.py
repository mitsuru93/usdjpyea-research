#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.usdjpy_portfolio_loss_cluster_phase1_v1.runner import main

if __name__ == "__main__":
    main()

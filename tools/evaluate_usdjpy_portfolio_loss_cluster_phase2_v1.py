#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.usdjpy_portfolio_loss_cluster_phase2_v1.runner import main
if __name__ == '__main__':
    main()

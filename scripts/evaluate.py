"""Run python scripts/evaluate.py tracker|matcher|detection."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation.cli import main

if __name__ == "__main__":
    main()

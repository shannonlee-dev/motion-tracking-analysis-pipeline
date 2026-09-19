"""Step 1: acquire and prepare the application inputs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datasets.workflow import main

if __name__ == "__main__":
    main("setup")

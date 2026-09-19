"""Step 2: verify decodable media, registration assets and evaluation annotations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datasets.workflow import main

if __name__ == "__main__":
    main("prepare")

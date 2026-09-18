"""Repository-relative dataset locations."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
CAVIAR_RAW_DIR = RAW_DIR / "caviar"
CAVIAR_MANIFEST = Path("data/manifests/caviar_sources.json")
LIGHTING_RAW_DIR = RAW_DIR / "lighting"
LIGHTING_MANIFEST = Path("data/manifests/lighting_sources.json")
LASIESTA_RAW_DIR = RAW_DIR / "lasiesta"
LASIESTA_MANIFEST = Path("data/manifests/lasiesta_sources.json")

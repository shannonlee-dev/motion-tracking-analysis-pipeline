"""Shared experiment protocol and repository-relative dataset locations.

Paths stay relative so callers can choose a repository/output root.
Dataset FPS values describe source material, independently of runtime fallback FPS.
"""
from pathlib import Path

CAVIAR_RAW_DIR = Path('data/raw')
CAVIAR_MANIFEST = Path('data/sources.json')
CAVIAR_FPS = 25
CAVIAR_FRAME_SIZE = (384, 288)
CAVIAR_SEQUENCES = ('walking', 'meeting', 'stopping')
ALOI_DIR = Path('data/aloi')
ALOI_RAW_DIR = ALOI_DIR / 'raw'
LASIESTA_DIR = Path('data/lasiesta')
LASIESTA_EXTRACTED_DIR = LASIESTA_DIR / 'extracted'
LASIESTA_FPS = 25
LASIESTA_FRAME_SIZE = (352, 288)
CLIPS_DIR = Path('data/clips')
CURRENT_RESULTS_DIR = Path('current')

EXPERIMENT_SEED = 42
EXPERIMENT_THREADS = 1
LEARNING_RATES = (0.001, 0.01, 0.1)
BASELINE_LEARNING_RATE = 0.01
KERNEL_SIZES = (1, 3, 7)
DISTANCE_LIMITS = (20, 80)
FEATURE_TRIALS = 10

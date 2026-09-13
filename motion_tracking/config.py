"""All algorithm defaults live here; CLI overrides are documented in README."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    learning_rate: float = 0.01
    history: int = 500
    var_threshold: float = 16
    min_area: float = 80
    max_area_fraction: float = 0.5
    kernel_size: int = 3
    max_distance: float = 50
    max_missing: int = 15
    trail_length: int = 80
    warmup_frames: int = 25
    predict_velocity: bool = False

    def __post_init__(self):
        if not 0 <= self.learning_rate <= 1:
            raise ValueError('learning_rate must be in [0, 1]')
        if self.kernel_size < 1 or self.kernel_size % 2 != 1:
            raise ValueError('kernel_size must be positive and odd')
        if not 0 < self.max_area_fraction <= 1:
            raise ValueError('max_area_fraction must be in (0, 1]')
        if min(self.history, self.min_area, self.max_distance, self.trail_length, self.var_threshold) <= 0:
            raise ValueError('history, area, distance, trail and variance must be positive')
        if min(self.max_missing, self.warmup_frames) < 0:
            raise ValueError('frame counts must be nonnegative')

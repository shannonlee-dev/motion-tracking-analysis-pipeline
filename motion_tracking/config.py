"""Motion/tracker configuration; CLI overrides are documented in README."""

import math
from dataclasses import dataclass, fields
from numbers import Integral


@dataclass(frozen=True)
class Config:
    # MOG2 배경 추정 알고리즘
    learning_rate: float = 0.01
    history: int = 500
    var_threshold: float = 16.0

    # 모션 감지
    min_area: float = 80.0
    max_area_fraction: float = 0.5
    kernel_size: int = 3
    open_kernel_size: int = 3
    # Opt-in: held-out crossings still show false joins (docs/report.md).
    compose_fragments: int = 0
    warmup_frames: int = 25

    # Tracker
    max_distance: float = 50
    max_missing: int = 15
    trail_length: int = 80

    def __post_init__(self) -> None:
        for field in fields(self):
            if not math.isfinite(getattr(self, field.name)):
                raise ValueError(f"{field.name} must be finite")

        for name in (
            "history",
            "kernel_size",
            "open_kernel_size",
            "compose_fragments",
            "warmup_frames",
            "max_missing",
            "trail_length",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise ValueError(f"{name} must be an integer")

        if not 0 <= self.learning_rate <= 1:
            raise ValueError("learning_rate must be in [0, 1]")

        if self.kernel_size < 1 or self.kernel_size % 2 == 0:
            raise ValueError("kernel_size must be positive and odd")
        if self.open_kernel_size < 1 or self.open_kernel_size % 2 == 0:
            raise ValueError("open_kernel_size must be positive and odd")
        if self.compose_fragments not in (0, 1):
            raise ValueError("compose_fragments must be 0 or 1")

        if not 0 < self.max_area_fraction <= 1:
            raise ValueError("max_area_fraction must be in (0, 1]")

        if (
            min(
                self.history,
                self.min_area,
                self.max_distance,
                self.trail_length,
                self.var_threshold,
            )
            <= 0
        ):
            raise ValueError(
                "history, area, distance, trail and variance must be positive"
            )

        if min(self.max_missing, self.warmup_frames) < 0:
            raise ValueError("frame counts must be nonnegative")


DEFAULT_CONFIG = Config()
# The CLI intentionally exposes only this subset of algorithm settings.
CLI_NUMERIC_FIELDS = (
    "learning_rate",
    "min_area",
    "max_distance",
    "kernel_size",
    "open_kernel_size",
    "compose_fragments",
    "max_missing",
    "warmup_frames",
)

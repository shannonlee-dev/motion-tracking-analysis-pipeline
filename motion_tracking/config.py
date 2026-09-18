"""Motion/tracker configuration; CLI overrides are documented in README."""

from dataclasses import dataclass


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
    warmup_frames: int = 25

    # Tracker
    max_distance: float = 50
    max_missing: int = 15
    trail_length: int = 80

    predict_velocity: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.learning_rate <= 1:
            raise ValueError("learning_rate must be in [0, 1]")

        if self.kernel_size < 1 or self.kernel_size % 2 == 0:
            raise ValueError("kernel_size must be positive and odd")

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
    "max_missing",
    "warmup_frames",
)
CLI_CONFIG_FIELDS = (*CLI_NUMERIC_FIELDS, "predict_velocity")

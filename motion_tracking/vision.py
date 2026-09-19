"""Compatibility imports for the original public Python interface."""

from motion_tracking.matching import MatchResult, TargetMatcher
from motion_tracking.motion import MotionDetector

__all__ = ["MotionDetector", "MatchResult", "TargetMatcher"]

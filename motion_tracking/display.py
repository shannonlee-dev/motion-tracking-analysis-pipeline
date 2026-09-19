"""Resolution-aware overlays and keyboard controls; no detection decisions."""

import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from motion_tracking.matching import MatchResult
from motion_tracking.tracker import Track

KEY_QUIT = ord("q")
KEY_PAUSE = ord("p")
KEY_SNAPSHOT = ord("s")
FONT = cv2.FONT_HERSHEY_SIMPLEX
BACKGROUND = (25, 25, 25)
WHITE = (255, 255, 255)
TARGET_COLOR = (0, 0, 255)


@dataclass(frozen=True)
class OverlayStyle:
    scale: float
    thickness: int
    padding: int
    line_height: int

    @classmethod
    def for_frame(cls, frame: np.ndarray) -> "OverlayStyle":
        scale = max(0.6, min(1.6, min(frame.shape[:2]) / 900))
        thickness = max(1, round(scale * 2))
        padding = max(3, round(scale * 6))
        (_, height), baseline = cv2.getTextSize(
            "FPS: 0123456789", FONT, scale, thickness
        )
        return cls(scale, thickness, padding, height + baseline + padding * 2)


def draw_label(
    image: np.ndarray,
    text: str,
    origin: tuple[int, int],
    style: OverlayStyle,
    background: tuple[int, int, int] = BACKGROUND,
) -> None:
    """Place a padded high-contrast label, keeping text inside the image."""
    height, width = image.shape[:2]
    pad = min(style.padding, max(0, (min(height, width) - 1) // 2))
    (text_width, _), _ = cv2.getTextSize(text, FONT, style.scale, style.thickness)
    scale = min(
        style.scale, style.scale * max(1, width - 2 * pad - 1) / max(1, text_width)
    )
    (text_width, text_height), baseline = cv2.getTextSize(
        text, FONT, scale, style.thickness
    )
    x = max(0, min(origin[0], width - text_width - 2 * pad - 1))
    y = max(0, min(origin[1], height - text_height - baseline - 2 * pad - 1))
    cv2.rectangle(
        image,
        (x, y),
        (
            min(width - 1, x + text_width + 2 * pad),
            min(height - 1, y + text_height + baseline + 2 * pad),
        ),
        background,
        -1,
    )
    cv2.putText(
        image,
        text,
        (x + pad, y + pad + text_height),
        FONT,
        scale,
        WHITE,
        style.thickness,
        cv2.LINE_AA,
    )


class Controls:
    def __init__(self) -> None:
        self.paused = False

    def handle(
        self,
        key: int,
        frame: np.ndarray | None,
        snapshot_dir: str | Path,
        frame_number: int,
    ) -> bool:
        if key == KEY_QUIT:
            return False

        if key == KEY_PAUSE:
            self.paused = not self.paused

        if key == KEY_SNAPSHOT and frame is not None:
            directory = Path(snapshot_dir)
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / f"frame_{frame_number:06d}_{time.time_ns()}.png"

            if not cv2.imwrite(str(path), frame):
                raise OSError(f"Cannot save snapshot: {path}")

        return True


def draw_overlay(
    frame: np.ndarray,
    tracks: Mapping[int, Track],
    fps: float,
    frame_number: int,
    match: MatchResult | None = None,
) -> np.ndarray:
    image = frame.copy()
    style = OverlayStyle.for_frame(frame)
    line = max(2, style.thickness)
    for tid, track in tracks.items():
        if track.missing:
            continue
        color = tuple(60 + (tid * factor) % 190 for factor in (73, 37, 109))
        x, y, w, h = track.bbox
        cv2.rectangle(image, (x, y), (x + w, y + h), color, line)
        draw_label(image, f"ID:{tid}", (x, max(0, y - style.line_height)), style)
        cv2.circle(image, tuple(map(int, track.center)), max(3, line), color, -1)
        if len(track.trail) > 1:
            cv2.polylines(image, [np.array(track.trail, np.int32)], False, color, line)

    draw_label(image, f"FPS: {fps:.1f}", (0, 0), style)
    draw_label(image, f"Frame: {frame_number}", (0, style.line_height), style)

    if match is not None and match.found and match.polygon is not None:
        x, y, w, h = cv2.boundingRect(match.polygon)
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(image.shape[1] - 1, x + w), min(image.shape[0] - 1, y + h)
        if x2 > x1 and y2 > y1:
            draw_label(
                image,
                "TARGET DETECTED",
                (x1, max(0, y1 - style.line_height)),
                style,
                TARGET_COLOR,
            )
            cv2.rectangle(image, (x1, y1), (x2, y2), TARGET_COLOR, max(3, line + 2))
    return image


class VideoDisplay:
    """OpenCV windows and timeline callbacks, separate from video processing."""

    MAIN_WINDOW = "Motion analysis | q quit, p pause, s snapshot"
    MASK_WINDOW = "Foreground mask"
    TIMELINE = "Timeline (frame)"

    def __init__(self, total_frames: int | None, show_mask: bool) -> None:
        self.seek_request: int | None = None
        self.syncing = False
        self.has_timeline = total_frames is not None and total_frames > 1
        self.show_mask = show_mask
        cv2.namedWindow(self.MAIN_WINDOW, cv2.WINDOW_NORMAL)
        if self.has_timeline:
            cv2.createTrackbar(
                self.TIMELINE, self.MAIN_WINDOW, 0, total_frames - 1, self.request_seek
            )
        if show_mask:
            cv2.namedWindow(self.MASK_WINDOW, cv2.WINDOW_NORMAL)

    def request_seek(self, position: int) -> None:
        if not self.syncing:
            self.seek_request = position

    def show(self, image: np.ndarray, mask: np.ndarray, frame_number: int) -> None:
        cv2.imshow(self.MAIN_WINDOW, image)
        if self.has_timeline:
            self.syncing = True
            try:
                cv2.setTrackbarPos(self.TIMELINE, self.MAIN_WINDOW, frame_number)
            finally:
                self.syncing = False
        if self.show_mask:
            cv2.imshow(self.MASK_WINDOW, mask)

    def read_key(self, delay: int) -> int | None:
        key = cv2.waitKey(delay) & 0xFF
        windows = (
            (self.MAIN_WINDOW, self.MASK_WINDOW)
            if self.show_mask
            else (self.MAIN_WINDOW,)
        )
        if any(
            cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1
            for window in windows
        ):
            return None
        return key

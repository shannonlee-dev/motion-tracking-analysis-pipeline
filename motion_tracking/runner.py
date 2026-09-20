"""OpenCV file/webcam analysis, interactive controls and reproducible exports."""

import csv
import os
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from motion_tracking.config import DEFAULT_CONFIG, Config
from motion_tracking.constants import (
    DEFAULT_SNAPSHOT_DIR,
    DEFAULT_VIDEO_FPS,
    MILLISECONDS_PER_SECOND,
    MIN_ELAPSED_SECONDS,
    VIDEO_CODEC,
)
from motion_tracking.display import Controls, VideoDisplay, draw_overlay
from motion_tracking.matching import MatchResult, TargetMatcher
from motion_tracking.motion import MotionDetector
from motion_tracking.tracker import Track, Tracker

TRACK_CSV_FIELDS = ("frame", "time_s", "track_id", "x", "y", "w", "h", "target_found")
PAUSED_POLL_MS = 30
CAMERA_STARTUP_TIMEOUT_SECONDS = 10.0
CAMERA_RETRY_INTERVAL_SECONDS = 0.1


@dataclass(frozen=True)
class FrameResult:
    """App measurements for synchronous observers; copy data before retaining it.

    Arrays and tracks belong to the running app and must not be mutated.
    """

    frame_number: int
    frame: np.ndarray
    mask: np.ndarray
    raw_mask: np.ndarray
    tracks: Mapping[int, Track]
    match: MatchResult | None
    target_keypoints: int
    binary_mask: np.ndarray | None = None
    opened_mask: np.ndarray | None = None
    boxes: tuple = ()
    component_boxes: tuple = ()


def _camera_error(source: int, reason: str) -> ValueError:
    return ValueError(
        f"Camera {source}: {reason}. Check camera permission for your terminal/IDE "
        "(macOS: System Settings > Privacy & Security > Camera), close other "
        "apps using the camera, and check the device connection or --source index."
    )


def _read_camera_startup(cap: cv2.VideoCapture, source: int) -> np.ndarray:
    # An opened camera can still be starting its asynchronous capture session.
    deadline = time.monotonic() + CAMERA_STARTUP_TIMEOUT_SECONDS
    while True:
        ok, frame = cap.read()
        if ok and frame is not None and frame.size:
            return frame
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _camera_error(source, "no frames received during startup")
        time.sleep(min(CAMERA_RETRY_INTERVAL_SECONDS, remaining))


def _validate_output_paths(
    source: int | str | Path,
    target: str | Path | None,
    output: str | Path | None,
    csv_path: str | Path | None,
) -> None:
    inputs = [Path(p).resolve() for p in (source, target) if isinstance(p, (str, Path))]
    outputs = [Path(p).resolve() for p in (output, csv_path) if p is not None]
    paths = inputs + outputs

    for index, path in enumerate(paths):
        for other_index in range(index):
            other = paths[other_index]

            if index < len(inputs):
                continue

            if path == other or (
                path.exists() and other.exists() and path.samefile(other)
            ):
                raise ValueError(
                    "Output path conflicts with an input or another output path"
                )


def _track_csv_rows(
    tracks: Mapping[int, Track],
    frame_number: int,
    source_fps: float,
    found: bool,
) -> list[list[int | float | str]]:
    rows = [
        [frame_number, frame_number / source_fps, tid, *track.bbox, int(found)]
        for tid, track in tracks.items()
        if track.missing == 0
    ]
    return rows or [
        [frame_number, frame_number / source_fps, "", "", "", "", "", int(found)]
    ]


def run(
    source: int | str | Path,
    config: Config | None = None,
    *,
    target: str | Path | None = None,
    headless: bool = False,
    output: str | Path | None = None,
    csv_path: str | Path | None = None,
    max_frames: int | None = None,
    snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    show_mask: bool = False,
    on_frame: Callable[[FrameResult], None] | None = None,
) -> dict[str, int | float]:
    config = config or DEFAULT_CONFIG

    if max_frames is not None and max_frames < 1:
        raise ValueError("max_frames must be positive")

    if (
        not headless
        # macOS uses Cocoa, which does not require X11/Wayland variables.
        and sys.platform == "linux"
        and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    ):
        raise ValueError(
            "No desktop display. Use --headless --output results/tracking-video.mp4"
        )

    _validate_output_paths(source, target, output, csv_path)

    matcher = TargetMatcher(cv2.imread(str(target))) if target else None
    cap = cv2.VideoCapture(source if isinstance(source, int) else str(source))
    writer, csv_file = None, None
    detector = MotionDetector(config)
    tracker = Tracker(
        config.max_distance,
        config.max_missing,
        config.trail_length,
    )
    controls, frame_number, elapsed, target_frames = Controls(), 0, 0.0, 0
    processed_frames = 0
    view: VideoDisplay | None = None
    image = None

    try:
        if not cap.isOpened():
            if isinstance(source, int):
                raise _camera_error(source, "cannot open device")
            raise ValueError(f"Cannot open video source: {source}")

        source_fps = cap.get(cv2.CAP_PROP_FPS)

        if not np.isfinite(source_fps) or source_fps <= 0:
            source_fps = DEFAULT_VIDEO_FPS

        if not headless:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            view = VideoDisplay(
                None if isinstance(source, int) else total_frames, show_mask
            )

        while max_frames is None or processed_frames < max_frames:
            tick = time.perf_counter()
            seeked = False

            if view is not None and view.seek_request is not None:
                requested_frame = view.seek_request
                view.seek_request = None
                if not cap.set(cv2.CAP_PROP_POS_FRAMES, requested_frame):
                    raise ValueError(f"Cannot seek to frame {requested_frame}")
                detector = MotionDetector(config)
                tracker = Tracker(
                    config.max_distance,
                    config.max_missing,
                    config.trail_length,
                )
                frame_number = requested_frame
                seeked = True

            if not controls.paused or seeked:
                if isinstance(source, int) and processed_frames == 0:
                    frame = _read_camera_startup(cap, source)
                    ok = True
                    tick = time.perf_counter()
                else:
                    ok, frame = cap.read()

                if not ok or frame is None or frame.size == 0:
                    if isinstance(source, int):
                        raise _camera_error(source, "no frames received during capture")
                    break

                boxes, mask = detector.detect(frame)
                component_boxes = tuple(boxes)
                if config.compose_fragments:
                    boxes = tracker.compose(boxes)
                tracks = tracker.update(boxes)

                match = matcher.match(frame) if matcher else None
                found = bool(match and match.found)
                target_frames += int(found)

                processing = time.perf_counter() - tick
                fps = 1 / max(processing, MIN_ELAPSED_SECONDS)
                image = draw_overlay(frame, tracks, fps, frame_number, match)

                if output:
                    if writer is None:
                        Path(output).parent.mkdir(parents=True, exist_ok=True)
                        height, width = image.shape[:2]
                        writer = cv2.VideoWriter(
                            str(output),
                            cv2.VideoWriter_fourcc(*VIDEO_CODEC),
                            source_fps,
                            (width, height),
                        )

                        if not writer.isOpened():
                            raise OSError(f"Cannot create video: {output}")

                    writer.write(image)

                if csv_path:
                    if csv_file is None:
                        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
                        csv_file = open(csv_path, "w", newline="", encoding="utf-8")
                        csv_writer = csv.writer(csv_file)
                        csv_writer.writerow(TRACK_CSV_FIELDS)
                    csv_writer.writerows(
                        _track_csv_rows(tracks, frame_number, source_fps, found)
                    )

                if view is not None:
                    view.show(image, mask, frame_number)

                if on_frame is not None:
                    on_frame(
                        FrameResult(
                            frame_number=frame_number,
                            frame=frame,
                            mask=mask,
                            raw_mask=detector.raw_mask,
                            tracks=tracks,
                            match=match,
                            target_keypoints=len(matcher.target_kp) if matcher else 0,
                            binary_mask=detector.binary_mask,
                            opened_mask=detector.opened_mask,
                            boxes=tuple(boxes),
                            component_boxes=component_boxes,
                        )
                    )

                elapsed += time.perf_counter() - tick
                frame_number += 1
                processed_frames += 1

            if view is not None:
                elapsed_ms = (time.perf_counter() - tick) * MILLISECONDS_PER_SECOND
                delay = (
                    PAUSED_POLL_MS
                    if controls.paused
                    else max(
                        1, round(MILLISECONDS_PER_SECOND / source_fps - elapsed_ms)
                    )
                )
                key = view.read_key(delay)
                if key is None:
                    break

                if not controls.handle(key, image, snapshot_dir, frame_number - 1):
                    break

        if processed_frames == 0:
            raise ValueError("Source contains no decodable frames")

        return dict(
            frames=processed_frames,
            fps=processed_frames / max(elapsed, MIN_ELAPSED_SECONDS),
            target_frames=target_frames,
        )
    finally:
        cap.release()

        if writer is not None:
            writer.release()

        if csv_file is not None:
            csv_file.close()

        if not headless:
            cv2.destroyAllWindows()

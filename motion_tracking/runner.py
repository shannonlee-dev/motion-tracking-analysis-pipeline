"""OpenCV file/webcam analysis, interactive controls and reproducible exports."""

import csv
import os
import time
from collections.abc import Mapping
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
from motion_tracking.display import Controls, draw_overlay
from motion_tracking.tracker import Track, Tracker
from motion_tracking.vision import MotionDetector, TargetMatcher


TRACK_CSV_FIELDS = ("frame", "time_s", "track_id", "x", "y", "w", "h", "target_found")
PAUSED_POLL_MS = 30
MAIN_WINDOW_TITLE = "Motion analysis | q quit, p pause, s snapshot"
MASK_WINDOW_TITLE = "Foreground mask"
TIMELINE_NAME = "Timeline (frame)"


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
) -> dict[str, int | float]:
    config = config or DEFAULT_CONFIG

    if max_frames is not None and max_frames < 1:
        raise ValueError("max_frames must be positive")

    if (
        not headless
        and os.name == "posix"
        and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    ):
        raise ValueError("No desktop display. Use --headless --output results/manual/videos/demo.mp4")

    _validate_output_paths(source, target, output, csv_path)

    matcher = TargetMatcher(cv2.imread(str(target))) if target else None
    cap = cv2.VideoCapture(source if isinstance(source, int) else str(source))
    writer, csv_file = None, None
    detector = MotionDetector(config)
    tracker = Tracker(
        config.max_distance,
        config.max_missing,
        config.trail_length,
        config.predict_velocity,
    )
    controls, frame_number, elapsed, target_frames = Controls(), 0, 0.0, 0
    processed_frames = 0
    timeline_request: int | None = None
    timeline_syncing = False
    image = None

    try:
        if not cap.isOpened():
            raise ValueError(f"Cannot open video source: {source}")

        source_fps = cap.get(cv2.CAP_PROP_FPS)

        if not np.isfinite(source_fps) or source_fps <= 0:
            source_fps = DEFAULT_VIDEO_FPS

        if csv_path:
            Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
            csv_file = open(csv_path, "w", newline="")
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(TRACK_CSV_FIELDS)

        if not headless:
            cv2.namedWindow(MAIN_WINDOW_TITLE, cv2.WINDOW_NORMAL)

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if not isinstance(source, int) and total_frames > 1:
                def request_timeline_position(position: int) -> None:
                    nonlocal timeline_request

                    if not timeline_syncing:
                        timeline_request = position

                cv2.createTrackbar(
                    TIMELINE_NAME,
                    MAIN_WINDOW_TITLE,
                    0,
                    total_frames - 1,
                    request_timeline_position,
                )

            if show_mask:
                cv2.namedWindow(MASK_WINDOW_TITLE, cv2.WINDOW_NORMAL)

        while max_frames is None or processed_frames < max_frames:
            tick = time.perf_counter()
            seeked = False

            if timeline_request is not None:
                requested_frame = timeline_request
                timeline_request = None
                cap.set(cv2.CAP_PROP_POS_FRAMES, requested_frame)
                detector = MotionDetector(config)
                tracker = Tracker(
                    config.max_distance,
                    config.max_missing,
                    config.trail_length,
                    config.predict_velocity,
                )
                frame_number = requested_frame
                seeked = True

            if not controls.paused or seeked:
                ok, frame = cap.read()

                if not ok:
                    break

                boxes, mask = detector.detect(frame)
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

                if csv_file:
                    csv_writer.writerows(
                        _track_csv_rows(tracks, frame_number, source_fps, found)
                    )

                if not headless:
                    cv2.imshow(MAIN_WINDOW_TITLE, image)

                    if not isinstance(source, int) and total_frames > 1:
                        timeline_syncing = True

                        try:
                            cv2.setTrackbarPos(
                                TIMELINE_NAME, MAIN_WINDOW_TITLE, frame_number
                            )
                        finally:
                            timeline_syncing = False

                    if show_mask:
                        cv2.imshow(MASK_WINDOW_TITLE, mask)

                elapsed += time.perf_counter() - tick
                frame_number += 1
                processed_frames += 1

            if not headless:
                elapsed_ms = (time.perf_counter() - tick) * MILLISECONDS_PER_SECOND
                delay = (
                    PAUSED_POLL_MS
                    if controls.paused
                    else max(1, round(MILLISECONDS_PER_SECOND / source_fps - elapsed_ms))
                )
                key = cv2.waitKey(delay) & 0xFF

                if (
                    cv2.getWindowProperty(MAIN_WINDOW_TITLE, cv2.WND_PROP_VISIBLE)
                    < 1
                    or (
                        show_mask
                        and cv2.getWindowProperty(
                            MASK_WINDOW_TITLE, cv2.WND_PROP_VISIBLE
                        )
                        < 1
                    )
                ):
                    break

                if not controls.handle(
                    key, image, snapshot_dir, frame_number - 1
                ):
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

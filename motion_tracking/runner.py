"""OpenCV file/webcam analysis, interactive controls and reproducible exports."""
import csv
import os
from pathlib import Path
import time
import cv2
import numpy as np
from motion_tracking.config import Config, DEFAULT_CONFIG
from motion_tracking.constants import (
    VIDEO_CODEC, DEFAULT_VIDEO_FPS, DEFAULT_SNAPSHOT_DIR,
    MIN_ELAPSED_SECONDS, MILLISECONDS_PER_SECOND,
)
from motion_tracking.tracker import Tracker
from motion_tracking.vision import MotionDetector, TargetMatcher
from motion_tracking.display import Controls, draw_overlay


TRACK_CSV_FIELDS = ('frame', 'time_s', 'track_id', 'x', 'y', 'w', 'h', 'target_found')
PAUSED_POLL_MS = 30
KEY_CODE_MASK = 0xff
MAIN_WINDOW_TITLE = 'Motion analysis | q quit, p pause, s snapshot'
MASK_WINDOW_TITLE = 'Foreground mask'


def run(
    source: int | str | Path, config: Config | None = None, *,
    target: str | Path | None = None, headless: bool = False,
    output: str | Path | None = None, csv_path: str | Path | None = None,
    max_frames: int | None = None, snapshot_dir: str | Path = DEFAULT_SNAPSHOT_DIR,
    show_mask: bool = False,
) -> dict[str, int | float]:
    config = config or DEFAULT_CONFIG
    if max_frames is not None and max_frames < 1:
        raise ValueError('max_frames must be positive')
    if not headless and os.name == 'posix' and not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        raise ValueError('No desktop display. Use --headless --output results/demo.mp4')
    inputs = [Path(p).resolve() for p in (source, target) if isinstance(p, (str, Path))]
    outputs = [Path(p).resolve() for p in (output, csv_path) if p is not None]
    paths = inputs + outputs
    for index, path in enumerate(paths):
        for other_index in range(index):
            other = paths[other_index]
            if index < len(inputs):
                continue
            if path == other or (path.exists() and other.exists() and path.samefile(other)):
                raise ValueError('Output path conflicts with an input or another output path')
    matcher = TargetMatcher(cv2.imread(str(target))) if target else None
    cap = cv2.VideoCapture(source if isinstance(source, int) else str(source))
    writer, csv_file = None, None
    detector = MotionDetector(config)
    tracker = Tracker(config.max_distance, config.max_missing, config.trail_length, config.predict_velocity)
    controls, frame_number, elapsed, target_frames = Controls(), 0, 0.0, 0
    image = None
    try:
        if not cap.isOpened():
            raise ValueError(f'Cannot open video source: {source}')
        source_fps = cap.get(cv2.CAP_PROP_FPS)
        if not np.isfinite(source_fps) or source_fps <= 0:
            source_fps = DEFAULT_VIDEO_FPS
        if csv_path:
            Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
            csv_file = open(csv_path, 'w', newline='')
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(TRACK_CSV_FIELDS)
        while max_frames is None or frame_number < max_frames:
            tick = time.perf_counter()
            if not controls.paused:
                ok, frame = cap.read()
                if not ok:
                    break
                boxes, mask = detector.detect(frame)
                tracks = tracker.update(boxes)
                match = matcher.match(frame) if matcher else None
                found = bool(match and match.found)
                target_frames += int(found)
                processing = time.perf_counter() - tick
                fps = 1/max(processing, MIN_ELAPSED_SECONDS)
                image = draw_overlay(frame, tracks, fps, frame_number, match)
                if output:
                    if writer is None:
                        Path(output).parent.mkdir(parents=True, exist_ok=True)
                        height, width = image.shape[:2]
                        writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*VIDEO_CODEC), source_fps, (width, height))
                        if not writer.isOpened():
                            raise OSError(f'Cannot create video: {output}')
                    writer.write(image)
                if csv_file:
                    visible = [(tid, t) for tid, t in tracks.items() if t.missing == 0]
                    for tid, track in visible:
                        csv_writer.writerow([frame_number, frame_number/source_fps, tid, *track.bbox, int(found)])
                    if not visible:
                        csv_writer.writerow([frame_number, frame_number/source_fps, '', '', '', '', '', int(found)])
                if not headless:
                    cv2.imshow(MAIN_WINDOW_TITLE, image)
                    if show_mask:
                        cv2.imshow(MASK_WINDOW_TITLE, mask)
                elapsed += time.perf_counter() - tick
                frame_number += 1
            if not headless:
                delay = PAUSED_POLL_MS if controls.paused else max(1, round(MILLISECONDS_PER_SECOND/source_fps - (time.perf_counter()-tick)*MILLISECONDS_PER_SECOND))
                if not controls.handle(cv2.waitKey(delay) & KEY_CODE_MASK, image, snapshot_dir, frame_number-1):
                    break
        if frame_number == 0:
            raise ValueError('Source contains no decodable frames')
        return dict(frames=frame_number, fps=frame_number/max(elapsed, MIN_ELAPSED_SECONDS), target_frames=target_frames)
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        if csv_file is not None:
            csv_file.close()
        if not headless:
            cv2.destroyAllWindows()

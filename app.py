"""OpenCV file/webcam analysis, interactive controls and reproducible exports."""
import argparse
import csv
import json
import os
from pathlib import Path
import time
import cv2
import numpy as np
from motion_tracking.config import Config
from motion_tracking.tracker import Tracker
from motion_tracking.vision import MotionDetector, TargetMatcher
from motion_tracking.display import Controls, draw_overlay


def run(source, config=None, *, target=None, headless=False, output=None, csv_path=None,
        max_frames=None, snapshot_dir='results/snapshots', show_mask=False):
    config = config or Config()
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
            source_fps = 25.0
        if csv_path:
            Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
            csv_file = open(csv_path, 'w', newline='')
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(['frame', 'time_s', 'track_id', 'x', 'y', 'w', 'h', 'target_found'])
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
                fps = 1/max(processing, 1e-9)
                image = draw_overlay(frame, tracks, fps, frame_number, match)
                if output:
                    if writer is None:
                        Path(output).parent.mkdir(parents=True, exist_ok=True)
                        height, width = image.shape[:2]
                        writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*'mp4v'), source_fps, (width, height))
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
                    cv2.imshow('Motion analysis | q quit, p pause, s snapshot', image)
                    if show_mask:
                        cv2.imshow('Foreground mask', mask)
                elapsed += time.perf_counter() - tick
                frame_number += 1
            if not headless:
                delay = 30 if controls.paused else max(1, round(1000/source_fps - (time.perf_counter()-tick)*1000))
                if not controls.handle(cv2.waitKey(delay) & 0xff, image, snapshot_dir, frame_number-1):
                    break
        if frame_number == 0:
            raise ValueError('Source contains no decodable frames')
        return dict(frames=frame_number, fps=frame_number/max(elapsed, 1e-9), target_frames=target_frames)
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        if csv_file is not None:
            csv_file.close()
        if not headless:
            cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='0', help='video path or numeric webcam index')
    parser.add_argument('--target')
    parser.add_argument('--output')
    parser.add_argument('--csv', dest='csv_path')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--show-mask', action='store_true')
    parser.add_argument('--max-frames', type=int)
    parser.add_argument('--snapshot-dir', default='results/snapshots')
    defaults = Config()
    for name in ('learning_rate', 'min_area', 'max_distance', 'kernel_size', 'max_missing', 'warmup_frames'):
        value = getattr(defaults, name)
        parser.add_argument('--'+name.replace('_', '-'), type=type(value), default=value)
    parser.add_argument('--predict-velocity', action='store_true')
    args = vars(parser.parse_args())
    try:
        config = Config(**{name: args.pop(name) for name in
                           ('learning_rate', 'min_area', 'max_distance', 'kernel_size', 'max_missing', 'warmup_frames', 'predict_velocity')})
        args['source'] = int(args['source']) if args['source'].isdigit() else args['source']
        print(json.dumps(run(config=config, **args), indent=2))
    except (ValueError, OSError, cv2.error) as error:
        parser.exit(2, f'Error: {error}\n')


if __name__ == '__main__':
    main()

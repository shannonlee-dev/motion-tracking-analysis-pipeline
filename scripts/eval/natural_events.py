"""Full LASIESTA sequences at three learning rates; visible-GT tracking evidence."""
from dataclasses import replace
import argparse
import xml.etree.ElementTree as ET
from scripts.constants import (
    LEARNING_RATES, BASELINE_LEARNING_RATE, CURRENT_RESULTS_DIR, LASIESTA_EXTRACTED_DIR, LASIESTA_FPS, LASIESTA_FRAME_SIZE,
)
from motion_tracking.constants import VIDEO_CODEC
import cv2
import numpy as np
from motion_tracking.display import draw_overlay
from motion_tracking.config import Config
from motion_tracking.tracker import Tracker
from motion_tracking.vision import MotionDetector
from motion_tracking.evaluation import assign_ground_truth, count_events
from scripts.common import ROOT, RESULTS, write_csv
from scripts.data.lasiesta import labels, sequence_paths, SINGLE_PERSON_LABELS

SEQUENCES = ('I_OC_01', 'I_OC_02', 'I_CA_01')
REVIEW_FRAMES = (90, 120, 137, 150, 160, 170, 171, 180, 189, 190, 200, 230, 267, 275, 300, 330)
PANEL_COLUMNS = 4


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-videos', action='store_true')
    args = parser.parse_args(argv)
    results = RESULTS/CURRENT_RESULTS_DIR
    (results/'captures').mkdir(parents=True, exist_ok=True)
    summaries, traces = [], []
    root = ROOT/LASIESTA_EXTRACTED_DIR
    for name in SEQUENCES:
        paths = sequence_paths(root, name)
        static = set()
        xml = root/f'{name}.xml'
        if xml.exists():
            for period in ET.parse(xml).findall('.//static_period'):
                static.update(range(int(period.findtext('start_frame')), int(period.findtext('final_frame'))+1))
        for rate in LEARNING_RATES:
            config = replace(Config(), learning_rate=rate)
            detector = MotionDetector(config)
            tracker = Tracker(max_distance=config.max_distance, max_missing=config.max_missing,
                              trail_length=config.trail_length, predict_velocity=config.predict_velocity)
            ids, excluded, panels, static_recall = [], [], [], []
            writer = None
            if rate == BASELINE_LEARNING_RATE and args.export_videos:
                (results/'videos').mkdir(parents=True, exist_ok=True)
                writer = cv2.VideoWriter(str(results/f'videos/{name}.mp4'),
                                         cv2.VideoWriter_fourcc(*VIDEO_CODEC), LASIESTA_FPS, LASIESTA_FRAME_SIZE)
                if not writer.isOpened():
                    raise OSError(f'Cannot create review video: {name}')
            try:
                for f, (image_path, gt_path) in enumerate(paths, 1):
                    image = cv2.imread(str(image_path))
                    gt = cv2.imread(str(gt_path))
                    if image is None or gt is None or image.shape != gt.shape:
                        raise ValueError(f'Missing/mismatched input/GT: {name} frame {f}')
                    foreground, _ = labels(gt)
                    # These supplied three sequences have one physical foreground person.
                    # White labels in I_CA_01 denote that same person's static period.
                    colored = np.unique(gt[foreground].reshape(-1, 3), axis=0)
                    if any(tuple(c) not in SINGLE_PERSON_LABELS for c in colored):
                        raise ValueError('Multiple/unsupported GT identities need per-object matching')
                    boxes, mask = detector.detect(image)
                    tracks = tracker.update(boxes)
                    truth = {1: cv2.boundingRect(foreground.astype('uint8'))} if foreground.any() else {}
                    matched = assign_ground_truth(truth, tracks).get(1)
                    skip = not truth or f <= config.warmup_frames
                    ids.append(matched)
                    excluded.append(skip)
                    state = 'visible' if truth else 'no_visible_GT'
                    if f in static:
                        state = 'stationary_official_XML'
                        if foreground.any():
                            static_recall.append(float(np.count_nonzero((mask > 0) & foreground)/foreground.sum()))
                    traces.append(dict(sequence=name, learning_rate=rate, frame=f, track_id=matched,
                                       excluded=int(skip), state=state, foreground_pixels=int(foreground.sum())))
                    if rate == BASELINE_LEARNING_RATE:
                        overlay = draw_overlay(image, tracks, 0, f)
                        cv2.putText(overlay, f'{name} GT={matched} {state}', (5, 280), 0, .36, (0, 255, 255), 1)
                        if writer is not None:
                            writer.write(overlay)
                        if f in REVIEW_FRAMES:
                            panels.append(overlay)
            finally:
                if writer is not None:
                    writer.release()
            metric = count_events(ids, excluded)
            eligible_static = [f-1 for f in sorted(static) if f <= len(paths) and not excluded[f-1]]
            metric.update(sequence=name, learning_rate=rate, frames=len(paths),
                          visible_frames=sum(not x for x in excluded),
                          missing_rate=metric['missing_frames']/metric['eligible_frames'] if metric['eligible_frames'] else '',
                          static_frames=len(eligible_static), static_missing=sum(ids[i] is None for i in eligible_static),
                          static_mean_pixel_recall=float(np.mean(static_recall)) if static_recall else '',
                          metric_scope='all confirmed ID changes; partial occlusion percentage not corrected')
            summaries.append(metric)
            if panels and name == 'I_CA_01':
                while len(panels) % PANEL_COLUMNS:
                    panels.append(np.zeros_like(panels[0]))
                cv2.imwrite(str(results/f'captures/{name}_events.jpg'), np.concatenate(
                    [np.concatenate(panels[i:i+PANEL_COLUMNS], axis=1) for i in range(0, len(panels), PANEL_COLUMNS)]))
            print(f'{name} lr={rate}: {len(paths)} frames, {metric["failures"]} loss runs', flush=True)
    write_csv(results/'lasiesta_tracking.csv', summaries)
    write_csv(results/'traces/lasiesta_tracking.csv', traces)


if __name__ == '__main__':
    main()

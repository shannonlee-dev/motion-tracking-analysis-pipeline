"""Command-line options for file/webcam motion analysis."""
import argparse
import json
import cv2
from motion_tracking.config import Config
from motion_tracking.runner import run


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

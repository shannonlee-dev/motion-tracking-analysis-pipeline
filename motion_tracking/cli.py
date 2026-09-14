"""Command-line options for file/webcam motion analysis."""
import argparse
import json
import cv2
from motion_tracking.config import Config, DEFAULT_CONFIG, CLI_NUMERIC_FIELDS, CLI_CONFIG_FIELDS
from motion_tracking.constants import DEFAULT_SNAPSHOT_DIR
from motion_tracking.runner import run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='0', help='video path or numeric webcam index')
    parser.add_argument('--target')
    parser.add_argument('--output')
    parser.add_argument('--csv', dest='csv_path')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--show-mask', action='store_true')
    parser.add_argument('--max-frames', type=int)
    parser.add_argument('--snapshot-dir', default=DEFAULT_SNAPSHOT_DIR)
    defaults = DEFAULT_CONFIG
    for name in CLI_NUMERIC_FIELDS:
        value = getattr(defaults, name)
        parser.add_argument('--'+name.replace('_', '-'), type=type(value), default=value)
    parser.add_argument('--predict-velocity', action='store_true')
    args = vars(parser.parse_args())

    try:
        # 설정 인자를 실행 인자와 분리
        config = Config(**{name: args.pop(name) for name in
                           CLI_CONFIG_FIELDS})

        if args['source'].isdigit():
            args['source'] = int(args['source'])

        print(json.dumps(run(config=config, **args), indent=2))
    except (ValueError, OSError, cv2.error) as error:
        parser.exit(2, f'Error: {error}\n')

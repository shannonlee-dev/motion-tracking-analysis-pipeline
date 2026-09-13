import csv
import cv2
import numpy as np
from app import run, Controls
from motion_tracking.config import Config
from motion_tracking.evaluation import count_events


def test_event_thresholds_and_occlusion_breaks_runs():
    assert count_events([1]*5+[2]*4+[1]*5, [False]*14)['id_switches'] == 0
    assert count_events([1]*5+[2]*5, [False]*10)['id_switches'] == 1
    assert count_events([1]*5+[None]*9, [False]*14)['failures'] == 0
    assert count_events([1]*5+[None]*20, [False]*25)['failures'] == 1
    assert count_events([1]*5+[None]*10, [False]*5+[True]*10)['failures'] == 0
    assert count_events([1]*5+[None]*5+[None]+[None]*5, [False]*10+[True]+[False]*5)['failures'] == 0


def test_id_change_must_be_consecutive():
    assert count_events([1]*5+[2]*3+[None]+[2]*3, [False]*12)['id_switches'] == 0
    assert count_events([1]*5+[None]*10+[2]*5, [False]*20)['id_switches'] == 1


def test_controls_pause_resume_snapshot_quit(tmp_path):
    controls = Controls()
    frame = np.full((30, 40, 3), 120, np.uint8)
    assert controls.handle(ord('p'), frame, tmp_path, 3)
    assert controls.paused
    controls.handle(ord('s'), frame, tmp_path, 3)
    saved = list(tmp_path.glob('*.png'))
    assert len(saved) == 1 and cv2.imread(str(saved[0])).shape == frame.shape
    controls.handle(ord('p'), frame, tmp_path, 3)
    assert not controls.paused
    assert not controls.handle(ord('q'), frame, tmp_path, 3)


def test_headless_video_roundtrip(tmp_path):
    source, output, trace = tmp_path/'input.avi', tmp_path/'output.mp4', tmp_path/'trace.csv'
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*'MJPG'), 10, (160, 120))
    assert writer.isOpened()
    for f in range(30):
        image = np.zeros((120, 160, 3), np.uint8)
        if f >= 5:
            image[40:70, f*2:f*2+20] = 255
        writer.write(image)
    writer.release()
    stats = run(str(source), Config(warmup_frames=5, min_area=30), headless=True,
                output=output, csv_path=trace)
    assert stats['frames'] == 30 and stats['fps'] > 0
    cap = cv2.VideoCapture(str(output))
    assert cap.isOpened() and int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 30
    cap.release()
    with trace.open() as handle:
        rows = list(csv.DictReader(handle))
    assert any(row['track_id'] for row in rows)
    assert max(int(row['frame']) for row in rows) == 29


def test_export_paths_cannot_destroy_inputs_or_each_other(tmp_path):
    import pytest
    source = tmp_path/'source.avi'
    source.write_bytes(b'original source')
    target = tmp_path/'target.png'
    target.write_bytes(b'original target')
    for kwargs in ({'csv_path':source}, {'output':target,'target':target},
                   {'output':tmp_path/'same','csv_path':tmp_path/'same'}):
        with pytest.raises(ValueError, match='path'):
            run(str(source), headless=True, **kwargs)
    assert source.read_bytes() == b'original source'
    assert target.read_bytes() == b'original target'


def test_invalid_cli_config_returns_clean_error():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, 'app.py', '--headless', '--learning-rate', '2'],
                            text=True, capture_output=True)
    assert result.returncode == 2
    assert 'learning_rate' in result.stderr
    assert 'Traceback' not in result.stderr

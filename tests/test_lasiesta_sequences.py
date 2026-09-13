import csv
import cv2
import numpy as np
import pytest
from scripts.eval import lighting as evaluate_lighting


def test_sequence_discovery_rejects_missing_middle_frame_and_missing_gt(tmp_path):
    discover = getattr(evaluate_lighting, 'sequence_paths', None)
    assert callable(discover), 'Complete sequence validation is missing'
    (tmp_path/'S').mkdir()
    (tmp_path/'S-GT').mkdir()
    for frame in (1, 3):
        (tmp_path/'S'/f'S-{frame}.bmp').touch()
        (tmp_path/'S-GT'/f'S-GT_{frame}.png').touch()
    with pytest.raises(ValueError):
        discover(tmp_path, 'S')
    (tmp_path/'S'/'S-2.bmp').touch()
    with pytest.raises(ValueError):
        discover(tmp_path, 'S')
    (tmp_path/'S-GT'/'S-GT_2.png').touch()
    pairs = discover(tmp_path, 'S')
    assert len(pairs) == 3
    assert pairs[1][0].name == 'S-2.bmp'


@pytest.mark.parametrize('export_videos', [False, True])
def test_lasiesta_runner_uses_all_frames_and_preserves_no_visible_gt_exclusion(tmp_path, monkeypatch, export_videos):
    from scripts.eval import natural_events as runner
    root = tmp_path/'data/lasiesta/extracted'
    for name in ('S', 'S-GT'):
        (root/name).mkdir(parents=True)
    black = np.zeros((288, 352, 3), dtype=np.uint8)
    for frame in range(1, 31):
        cv2.imwrite(str(root/'S'/f'S-{frame}.bmp'), black)
        cv2.imwrite(str(root/'S-GT'/f'S-GT_{frame}.png'), black)
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'RESULTS', tmp_path/'results')
    monkeypatch.setattr(runner, 'SEQUENCES', ('S', 'S', 'S'))
    historical = tmp_path/'results/lasiesta_tracking.csv'
    historical.parent.mkdir()
    historical.write_text('historical evidence\n')
    runner.main(['--export-videos'] if export_videos else [])
    assert historical.read_text() == 'historical evidence\n'
    with (tmp_path/'results/current/lasiesta_tracking.csv').open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 9
    assert {r['learning_rate'] for r in rows} == {'0.001', '0.01', '0.1'}
    assert all(r['frames'] == '30' and r['excluded_frames'] == '30' for r in rows)
    assert all(r['failures'] == '0' and r['eligible_frames'] == '0' for r in rows)
    assert not list(tmp_path.rglob('natural_events.csv'))
    videos = list(tmp_path.rglob('*.mp4'))
    if export_videos:
        assert videos == [tmp_path/'results/current/videos/S.mp4']
        cap = cv2.VideoCapture(str(videos[0]))
        assert cap.isOpened() and int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 30
        cap.release()
    else:
        assert not videos

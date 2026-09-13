from scripts.data.synthetic import synthetic_frame
from scripts.data.caviar import load_caviar
from motion_tracking.evaluation import assign_ground_truth
from motion_tracking.tracker import Tracker


def test_synthetic_occlusion_and_pause_are_known():
    _, truth, excluded = synthetic_frame('crossing', 0, 300)
    assert len(truth) == 2 and excluded[1] and not excluded[2]
    _, a, _ = synthetic_frame('stopping', 0, 250)
    _, b, _ = synthetic_frame('stopping', 0, 350)
    assert a == b
    _, truth, _ = synthetic_frame('single', 0, 10)
    assert truth == {}


def test_gt_assignment_excludes_retained_tracks():
    tracker = Tracker()
    tracker.update([(10, 10, 20, 20)])
    assert assign_ground_truth({7:(10,10,20,20)}, tracker.tracks) == {7:1}
    tracker.update([])
    assert assign_ground_truth({7:(10,10,20,20)}, tracker.tracks) == {7:None}


def test_caviar_center_to_top_left_and_group_exclusion(tmp_path):
    path = tmp_path/'gt.xml'
    path.write_text('<dataset><frame number="0"><objectlist><object id="3"><box xc="30" yc="40" w="20" h="10"/></object></objectlist><grouplist><group id="0"/></grouplist></frame></dataset>')
    assert load_caviar(path) == {0:{3:(20.,35.,20.,10.)}}


def test_excluded_rear_object_does_not_steal_detection():
    from scripts.eval.tracking import match_eligible
    truth = {1:(100,100,30,48),2:(100,100,30,48)}
    tracker = Tracker()
    tracker.update([(100,100,30,48)])
    assert match_eligible(truth, tracker.tracks, {1:True,2:False}) == {1:None,2:1}


def test_tracking_exports_metrics_without_creating_videos(tmp_path, monkeypatch):
    from scripts.eval import tracking as runner
    from motion_tracking.config import Config
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'RESULTS', tmp_path/'results')
    monkeypatch.setattr(runner, 'CONDITIONS', {'single': 1})
    for name in ('data/clips', 'results/videos', 'results/traces', 'results/captures'):
        (tmp_path/name).mkdir(parents=True)
    rows = runner.evaluate_synthetic(Config(), 'baseline', export=True)
    assert len(rows) == 1 and rows[0]['eligible_frames'] == 525
    assert rows[0]['failures'] == rows[0]['id_switches'] == 0
    assert (tmp_path/'results/synthetic_objects.csv').is_file()
    assert (tmp_path/'results/traces/single_01.csv').is_file()
    assert not list(tmp_path.rglob('*.mp4'))


def test_optional_video_export_keeps_tracking_measurements_identical(tmp_path, monkeypatch):
    from scripts.eval import tracking as runner
    from motion_tracking.config import Config
    import cv2
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'RESULTS', tmp_path/'results')
    monkeypatch.setattr(runner, 'CONDITIONS', {'single': 2})
    for name in ('data/clips', 'results/videos', 'results/traces', 'results/captures'):
        (tmp_path/name).mkdir(parents=True)
    plain = runner.evaluate_synthetic(Config(), 'baseline', export=True)
    exported = runner.evaluate_synthetic(Config(), 'baseline', export=True, export_videos=True)
    assert plain == exported
    cap = cv2.VideoCapture(str(tmp_path/'data/clips/single_01.mp4'))
    assert cap.isOpened() and int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 625
    cap.release()
    cap = cv2.VideoCapture(str(tmp_path/'results/videos/single_02.mp4'))
    assert cap.isOpened() and int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 625
    cap.release()


def test_crossing_runner_exports_post_separation_metric(tmp_path, monkeypatch):
    import csv
    from scripts.eval import tracking as runner
    from motion_tracking.config import Config
    monkeypatch.setattr(runner, 'RESULTS', tmp_path)
    monkeypatch.setattr(runner, 'CONDITIONS', {'crossing': 2, 'single': 1})
    (tmp_path/'captures').mkdir()
    rows = runner.evaluate_synthetic(Config(), 'baseline', export=True)
    # Trial 2 changes ID during overlap; only two changes persist after separation.
    assert rows[1].get('post_overlap_switches') == 2
    assert rows[1]['id_switches'] == 3
    assert (rows[1]['overlap_start'], rows[1]['overlap_end']) == (264, 340)
    assert rows[2]['post_overlap_switches'] == ''  # No overlap is not a measured zero.
    with (tmp_path/'synthetic_objects.csv').open() as handle:
        objects = [r for r in csv.DictReader(handle) if r['video'] == 'crossing_02']
    assert sum(int(r['post_overlap_switches']) for r in objects) == 2


def test_caviar_download_preserves_historical_sources(tmp_path, monkeypatch):
    import json
    from scripts.data import download
    monkeypatch.setattr(download, 'ROOT', tmp_path)
    raw = tmp_path/'data/raw'
    raw.mkdir(parents=True)
    historical = dict(file='crossing.mpg', sha256='historical', bytes=123)
    manifest = tmp_path/'data/sources.json'
    manifest.write_text(json.dumps([historical]))
    for name in download.SOURCES:
        (raw/name).write_bytes(b'cached source')
    download.main()
    records = json.loads(manifest.read_text())
    assert records[0] == historical
    assert len(records) == 7
    assert {r['file'] for r in records[1:]} == {
        f'{name}.{ext}' for name in ('meeting', 'walking', 'stopping') for ext in ('mpg', 'xml')}

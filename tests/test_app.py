import csv
import json
import subprocess
import sys

import cv2
import numpy as np
import pytest

from motion_tracking.config import Config
from motion_tracking.display import Controls, draw_overlay
from motion_tracking.matching import MatchResult
from motion_tracking.motion import MotionDetector
from motion_tracking.runner import run


def test_target_match_draws_a_clipped_red_box_and_local_label():
    frame = np.zeros((100, 320, 3), np.uint8)
    polygon = np.array([[[40, 30]], [[100, 30]], [[100, 80]], [[40, 80]]], np.int32)

    image = draw_overlay(
        frame,
        {},
        fps=30.0,
        frame_number=12,
        match=MatchResult(found=True, polygon=polygon),
    )

    assert tuple(image[30, 40]) == (0, 0, 255)
    assert tuple(image[80, 100]) == (0, 0, 255)
    assert np.any(np.all(image[15:30, 40:150] == (0, 0, 255), axis=2))
    assert not np.any(np.all(image[25:55, :30] == (0, 0, 255), axis=2))


def test_target_box_is_absent_when_match_is_not_found_and_clipped_at_frame_edges():
    frame = np.zeros((80, 60, 3), np.uint8)
    polygon = np.array([[[-10, 30]], [[20, 30]], [[20, 60]], [[-10, 60]]], np.int32)

    absent = draw_overlay(
        frame,
        {},
        fps=30.0,
        frame_number=1,
        match=MatchResult(found=False, polygon=polygon),
    )
    present = draw_overlay(
        frame,
        {},
        fps=30.0,
        frame_number=1,
        match=MatchResult(found=True, polygon=polygon),
    )

    assert not np.any(np.all(absent == (0, 0, 255), axis=2))
    assert tuple(present[30, 0]) == (0, 0, 255)


def test_controls_pause_resume_snapshot_quit(tmp_path):
    controls = Controls()
    frame = np.full((30, 40, 3), 120, np.uint8)
    assert controls.handle(ord("p"), frame, tmp_path, 3)
    assert controls.paused
    controls.handle(ord("s"), frame, tmp_path, 3)
    saved = list(tmp_path.glob("*.png"))
    assert len(saved) == 1 and cv2.imread(str(saved[0])).shape == frame.shape
    controls.handle(ord("p"), frame, tmp_path, 3)
    assert not controls.paused
    assert not controls.handle(ord("q"), frame, tmp_path, 3)


@pytest.mark.parametrize(
    ("show_mask", "closed_title"),
    [
        (False, "Motion analysis | q quit, p pause, s snapshot"),
        (True, "Foreground mask"),
    ],
)
def test_closing_a_display_window_stops_playback(
    tmp_path, monkeypatch, show_mask, closed_title
):
    source = tmp_path / "input.avi"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"MJPG"), 10, (32, 24))
    assert writer.isOpened()

    for _ in range(3):
        writer.write(np.zeros((24, 32, 3), np.uint8))

    writer.release()
    monkeypatch.setenv("DISPLAY", ":test")
    monkeypatch.setattr(cv2, "namedWindow", lambda *_: None)
    monkeypatch.setattr(cv2, "createTrackbar", lambda *_: None)
    monkeypatch.setattr(cv2, "setTrackbarPos", lambda *_: None)
    monkeypatch.setattr(cv2, "imshow", lambda *_: None)
    monkeypatch.setattr(cv2, "waitKey", lambda _: -1)
    monkeypatch.setattr(
        cv2,
        "getWindowProperty",
        lambda title, _: 0.0 if title == closed_title else 1.0,
    )
    monkeypatch.setattr(cv2, "destroyAllWindows", lambda: None)

    stats = run(str(source), show_mask=show_mask)

    assert stats["frames"] == 1


def test_closing_the_window_while_paused_stops_playback(tmp_path, monkeypatch):
    source = tmp_path / "input.avi"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"MJPG"), 10, (32, 24))
    assert writer.isOpened()

    for _ in range(3):
        writer.write(np.zeros((24, 32, 3), np.uint8))

    writer.release()
    keys = iter((ord("p"), -1, ord("p")))
    visibility = iter((1.0, 0.0))
    monkeypatch.setenv("DISPLAY", ":test")
    monkeypatch.setattr(cv2, "namedWindow", lambda *_: None)
    monkeypatch.setattr(cv2, "createTrackbar", lambda *_: None)
    monkeypatch.setattr(cv2, "setTrackbarPos", lambda *_: None)
    monkeypatch.setattr(cv2, "imshow", lambda *_: None)
    monkeypatch.setattr(cv2, "waitKey", lambda _: next(keys, -1))
    monkeypatch.setattr(cv2, "getWindowProperty", lambda *_: next(visibility, 0.0))
    monkeypatch.setattr(cv2, "destroyAllWindows", lambda: None)

    stats = run(str(source))

    assert stats["frames"] == 1


def test_file_gui_adds_timeline_and_seeks_to_selected_frame(tmp_path, monkeypatch):
    import motion_tracking.runner as runner

    resets = {"detector": 0, "tracker": 0}
    detector_class, tracker_class = runner.MotionDetector, runner.Tracker

    def detector(*args):
        resets["detector"] += 1
        return detector_class(*args)

    def tracker(*args):
        resets["tracker"] += 1
        return tracker_class(*args)

    monkeypatch.setattr(runner, "MotionDetector", detector)
    monkeypatch.setattr(runner, "Tracker", tracker)
    source = tmp_path / "input.avi"
    trace = tmp_path / "trace.csv"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"MJPG"), 10, (32, 24))
    assert writer.isOpened()

    for value in range(4):
        writer.write(np.full((24, 32, 3), value * 50, np.uint8))

    writer.release()
    created = []
    positions = []
    callback = None

    def create_trackbar(name, window, initial, maximum, handler):
        nonlocal callback
        created.append((name, window, initial, maximum))
        callback = handler

    calls = 0

    def wait_key(_):
        nonlocal calls
        calls += 1

        if calls == 1:
            callback(3)
            return -1

        return ord("q")

    monkeypatch.setenv("DISPLAY", ":test")
    monkeypatch.setattr(cv2, "namedWindow", lambda *_: None)
    monkeypatch.setattr(cv2, "createTrackbar", create_trackbar)
    monkeypatch.setattr(
        cv2, "setTrackbarPos", lambda name, window, position: positions.append(position)
    )
    monkeypatch.setattr(cv2, "imshow", lambda *_: None)
    monkeypatch.setattr(cv2, "waitKey", wait_key)
    monkeypatch.setattr(cv2, "getWindowProperty", lambda *_: 1.0)
    monkeypatch.setattr(cv2, "destroyAllWindows", lambda: None)

    stats = run(str(source), csv_path=trace)

    assert created == [
        ("Timeline (frame)", "Motion analysis | q quit, p pause, s snapshot", 0, 3)
    ]
    assert resets == {"detector": 2, "tracker": 2}
    assert positions == [0, 3]
    assert stats["frames"] == 2

    with trace.open() as stream:
        assert [int(row["frame"]) for row in csv.DictReader(stream)] == [0, 3]


def test_timeline_updates_an_adjacent_frame_while_paused(tmp_path, monkeypatch):
    source = tmp_path / "input.avi"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"MJPG"), 10, (32, 24))
    assert writer.isOpened()

    for value in range(3):
        writer.write(np.full((24, 32, 3), value * 50, np.uint8))

    writer.release()
    callback = None

    def create_trackbar(_, __, ___, ____, handler):
        nonlocal callback
        callback = handler

    calls = 0

    def wait_key(_):
        nonlocal calls
        calls += 1

        if calls == 1:
            return ord("p")

        if calls == 2:
            callback(1)
            return -1

        return ord("q")

    monkeypatch.setenv("DISPLAY", ":test")
    monkeypatch.setattr(cv2, "namedWindow", lambda *_: None)
    monkeypatch.setattr(cv2, "createTrackbar", create_trackbar)
    monkeypatch.setattr(cv2, "setTrackbarPos", lambda *_: None)
    monkeypatch.setattr(cv2, "imshow", lambda *_: None)
    monkeypatch.setattr(cv2, "waitKey", wait_key)
    monkeypatch.setattr(cv2, "getWindowProperty", lambda *_: 1.0)
    monkeypatch.setattr(cv2, "destroyAllWindows", lambda: None)

    assert run(str(source))["frames"] == 2


@pytest.mark.parametrize("entrypoint", [None, ["app.py"], ["-m", "motion_tracking"]])
def test_headless_video_roundtrip(tmp_path, entrypoint):
    source, output, trace = (
        tmp_path / "input.avi",
        tmp_path / "output.mp4",
        tmp_path / "trace.csv",
    )
    writer = cv2.VideoWriter(
        str(source), cv2.VideoWriter_fourcc(*"MJPG"), 10, (160, 120)
    )
    assert writer.isOpened()

    for f in range(30):
        image = np.zeros((120, 160, 3), np.uint8)

        if f >= 5:
            image[40:70, f * 2 : f * 2 + 20] = 255

        writer.write(image)

    writer.release()

    if entrypoint is None:
        stats = run(
            str(source),
            Config(warmup_frames=5, min_area=30),
            headless=True,
            output=output,
            csv_path=trace,
        )
    else:
        result = subprocess.run(
            [
                sys.executable,
                *entrypoint,
                "--source",
                str(source),
                "--headless",
                "--warmup-frames",
                "5",
                "--min-area",
                "30",
                "--output",
                str(output),
                "--csv",
                str(trace),
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        stats = json.loads(result.stdout)

    assert stats["frames"] == 30 and stats["fps"] > 0
    cap = cv2.VideoCapture(str(output))
    assert cap.isOpened() and int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 30
    cap.release()

    with trace.open() as handle:
        rows = list(csv.DictReader(handle))

    assert any(row["track_id"] for row in rows)
    assert max(int(row["frame"]) for row in rows) == 29


def test_export_paths_cannot_destroy_inputs_or_each_other(tmp_path):
    source = tmp_path / "source.avi"
    source.write_bytes(b"original source")
    target = tmp_path / "target.png"
    target.write_bytes(b"original target")

    for kwargs in (
        {"csv_path": source},
        {"output": target, "target": target},
        {"output": tmp_path / "same", "csv_path": tmp_path / "same"},
    ):
        with pytest.raises(ValueError, match="path"):
            run(str(source), headless=True, **kwargs)

    assert source.read_bytes() == b"original source"
    assert target.read_bytes() == b"original target"


@pytest.mark.parametrize("entrypoint", [["app.py"], ["-m", "motion_tracking"]])
def test_invalid_cli_config_returns_clean_error(entrypoint):
    result = subprocess.run(
        [sys.executable, *entrypoint, "--headless", "--learning-rate", "2"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "learning_rate" in result.stderr
    assert "Traceback" not in result.stderr

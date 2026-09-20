"""Camera startup failures must not be treated as file EOF."""

import cv2
import numpy as np
import pytest

from motion_tracking import runner


class Capture:
    def __init__(self, frames, opened=True):
        self.frames = iter(frames)
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def get(self, prop):
        return 30

    def read(self):
        frame = next(self.frames, None)
        return frame is not None, frame

    def release(self):
        self.released = True


@pytest.fixture
def camera(monkeypatch):
    clock = [0.0]

    def sleep(seconds):
        clock[0] += seconds
        assert clock[0] < 20, "Camera startup must time out"

    monkeypatch.setattr(runner.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(runner.time, "sleep", sleep)

    def install(frames, opened=True):
        capture = Capture(frames, opened)
        monkeypatch.setattr(cv2, "VideoCapture", lambda source: capture)
        return capture

    return install


def test_camera_waits_for_initial_frames(camera, tmp_path):
    frame = np.zeros((24, 32, 3), np.uint8)
    capture = camera([None, None, frame, frame])
    trace = tmp_path / "trace.csv"

    stats = runner.run(0, headless=True, max_frames=2, csv_path=trace)

    assert stats["frames"] == 2
    assert len(trace.read_text().splitlines()) == 3
    assert capture.released


def test_camera_startup_timeout_explains_how_to_recover(camera):
    capture = camera([])

    with pytest.raises(ValueError, match=r"Camera 0.*permission"):
        runner.run(0, headless=True, max_frames=1)

    assert capture.released


def test_unopened_camera_explains_how_to_recover(camera):
    capture = camera([], opened=False)

    with pytest.raises(ValueError, match=r"Camera 0.*permission"):
        runner.run(0, headless=True, max_frames=1)

    assert capture.released


def test_empty_file_still_fails_without_camera_retries(camera, monkeypatch):
    capture = camera([])

    def unexpected_sleep(_):
        pytest.fail("File EOF must not wait for camera startup")

    monkeypatch.setattr(runner.time, "sleep", unexpected_sleep)
    with pytest.raises(ValueError, match="Source contains no decodable frames"):
        runner.run("empty.mp4", headless=True)

    assert capture.released

"""Preparation rejects changed inputs and never rewrites healthy cached bytes."""

import hashlib
import json
import subprocess
import sys
import zipfile

import cv2
import numpy as np
import pytest

from datasets import detection, tracker
from datasets.paths import ROOT, tracker_input
from datasets.storage import download, extract, sha256, verify


def test_cached_download_is_pinned_and_idempotent(tmp_path, monkeypatch):
    path = tmp_path / "source.bin"
    path.write_bytes(b"original")
    record = dict(bytes=8, sha256=sha256(path))
    before = path.stat().st_mtime_ns
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: pytest.fail("cached data must not use network"),
    )
    assert download(path, "https://unused.invalid", record) == path
    assert path.stat().st_mtime_ns == before
    path.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="Checksum"):
        download(path, "https://unused.invalid", record)
    assert path.read_bytes() == b"corrupted"


def test_failed_download_does_not_publish_partial_file(tmp_path, monkeypatch):
    from io import BytesIO

    path = tmp_path / "source.bin"
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: BytesIO(b"bad"))
    with pytest.raises(ValueError, match="Checksum"):
        download(path, "https://unused.invalid", dict(sha256="0" * 64))
    assert list(tmp_path.iterdir()) == []


def test_zip_extraction_is_safe_and_idempotent(tmp_path):
    archive = tmp_path / "data.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("frames/001.bmp", b"frame")
    out = tmp_path / "out"
    extract(archive, out)
    frame = out / "frames/001.bmp"
    before = frame.stat().st_mtime_ns
    extract(archive, out)
    assert frame.read_bytes() == b"frame" and frame.stat().st_mtime_ns == before
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("../escape.txt", b"bad")
    with pytest.raises(ValueError, match="Unsafe"):
        extract(archive, out)
    assert not (tmp_path / "escape.txt").exists()


def test_tracker_paths_do_not_depend_on_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert tracker_input(1) == ROOT / "data/tracker/inputs/01.mpg"
    assert tracker_input("19") == ROOT / "data/tracker/inputs/19.mp4"
    with pytest.raises(ValueError):
        tracker_input(20)


def test_registration_uses_recorded_frame_and_crop(tmp_path, monkeypatch):
    root = tmp_path
    directory = root / "data/detection"
    (directory / "reference").mkdir(parents=True)
    (directory / "raw").mkdir()
    source = directory / "raw/town_centre.mp4"
    source.write_bytes(b"stub video")
    frame = np.arange(40 * 50 * 3, dtype=np.uint8).reshape(40, 50, 3)
    crop = frame[5:25, 10:30]
    _, encoded = cv2.imencode(".png", crop)
    record = dict(
        path="data/detection/raw/town_centre.mp4",
        bytes=10,
        sha256=sha256(source),
        target=dict(
            path="data/detection/inputs/target.png",
            frame=5800,
            bbox_xywh=[10, 5, 20, 20],
            sha256=hashlib.sha256(encoded).hexdigest(),
            bytes=len(encoded),
        ),
    )
    (directory / "reference/source.json").write_text(json.dumps(record))

    class Capture:
        def __init__(self, path):
            pass

        def set(self, key, value):
            assert value == 5800

        def read(self):
            return True, frame

        def release(self):
            pass

    monkeypatch.setattr(detection, "ROOT", root)
    monkeypatch.setattr(detection, "DETECTION", directory)
    monkeypatch.setattr(cv2, "VideoCapture", Capture)
    detection.prepare(offline=True)
    target = directory / "inputs/target.png"
    assert np.array_equal(cv2.imread(str(target)), crop)
    before = target.stat().st_mtime_ns
    detection.prepare(offline=True)
    assert target.stat().st_mtime_ns == before


@pytest.mark.parametrize(
    "script", ["01_setup_data.py", "02_verify_data.py"]
)
def test_script_help_works_outside_repository(tmp_path, script):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_workflow_rejects_unknown_stage():
    from datasets.workflow import main

    with pytest.raises(ValueError, match="Unknown workflow stage"):
        main("prepare")


def test_learning_rate_fails_before_output_without_raw_ground_truth(
    tmp_path, monkeypatch
):
    from experiments import learning_rate

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(learning_rate, "TRACKER", tmp_path / "tracker")
    with pytest.raises(ValueError, match="Learning-rate ground truth is missing"):
        learning_rate.main([])
    assert not (tmp_path / "results").exists()


def test_all_pinned_public_inputs_match_manifest():
    for purpose in ("tracker", "matcher"):
        manifest = ROOT / "data" / purpose / "reference/input_integrity.json"
        for record in json.loads(manifest.read_text()):
            verify(ROOT / record["path"], record)


@pytest.mark.parametrize("same_encoder", [True, False])
def test_missing_tracker_video_reconstructs_then_skips_writes(
    tmp_path, monkeypatch, same_encoder
):
    from datasets.media import convert_bmps

    root = tmp_path
    directory = root / "data/tracker"
    frames = directory / "raw/lasiesta/sequence"
    frames.mkdir(parents=True)
    for index in range(2):
        cv2.imwrite(
            str(frames / f"{index}.bmp"), np.full((24, 32, 3), index * 60, np.uint8)
        )
    archive = frames.parent / "sequence.rar"
    archive.write_bytes(b"archive placeholder")
    expected = root / "expected.mp4"
    convert_bmps(frames, expected, 25)
    key = "data/tracker/inputs/15.mp4"
    record = dict(
        path=key,
        bytes=expected.stat().st_size,
        sha256=sha256(expected) if same_encoder else "0" * 64,
    )
    reference = directory / "reference"
    reference.mkdir()
    (reference / "input_integrity.json").write_text(json.dumps([record]))
    generated = directory / "generated"
    generated.mkdir()
    (generated / "inputs.json").write_text(
        json.dumps({key: dict(bytes=9, sha256="1" * 64)})
    )
    recipe = dict(file="sequence.rar", url="unused", local_file=key, frames=2, fps=25)
    monkeypatch.setattr(tracker, "ROOT", root)
    monkeypatch.setattr(tracker, "TRACKER", directory)
    monkeypatch.setattr(
        tracker, "records", lambda name: [recipe] if name == "lasiesta" else []
    )
    monkeypatch.setattr(tracker, "download", lambda *a, **k: archive)
    monkeypatch.setattr(tracker, "extract", lambda *a: None)
    tracker.prepare(offline=True)
    output = root / key
    assert output.read_bytes() == expected.read_bytes()
    ledger = json.loads((generated / "inputs.json").read_text())
    assert (
        (key not in ledger)
        if same_encoder
        else (ledger[key]["sha256"] == sha256(expected))
    )
    before = output.stat().st_mtime_ns
    tracker.prepare(offline=True)
    assert output.stat().st_mtime_ns == before


def test_readiness_rejects_incomplete_known_sequence(tmp_path):
    from datasets.workflow import check_video

    path = tmp_path / "short.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 25, (32, 24))
    writer.write(np.zeros((24, 32, 3), np.uint8))
    writer.release()
    with pytest.raises(ValueError, match="Incomplete"):
        check_video(path, 307)

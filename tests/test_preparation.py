"""Preparation rejects changed inputs and never rewrites healthy cached bytes."""

import json
import ssl
import subprocess
import sys
import zipfile

import cv2
import numpy as np
import pytest

from motion_tracking.datasets import detection, tracker
from motion_tracking.datasets.paths import ROOT, tracker_input
from motion_tracking.datasets.storage import download, extract, sha256, verify


def test_download_uses_macos_ca_when_python_has_no_certificates(tmp_path, monkeypatch):
    from io import BytesIO
    from pathlib import Path

    from motion_tracking.datasets import storage

    if not Path("/etc/ssl/cert.pem").is_file():
        pytest.skip("macOS system CA bundle is not available")
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    monkeypatch.setattr(ssl, "create_default_context", lambda: context)

    def open_verified(url, *, timeout, context=None):
        assert context is not None
        assert context.cert_store_stats()["x509_ca"] > 0
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname
        return BytesIO(b"source")

    monkeypatch.setattr(storage.urllib.request, "urlopen", open_verified)
    expected = tmp_path / "expected"
    expected.write_bytes(b"source")
    output = tmp_path / "download"
    download(output, "https://example.invalid/source", dict(sha256=sha256(expected)))
    assert output.read_bytes() == b"source"


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


@pytest.mark.parametrize("variable", ["SSL_CERT_FILE", "SSL_CERT_DIR"])
def test_download_preserves_explicit_ca_configuration(monkeypatch, variable):
    from motion_tracking.datasets.storage import download_ssl_context

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv(variable, "/custom/trust")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    monkeypatch.setattr(ssl, "create_default_context", lambda: context)
    configured = download_ssl_context()
    assert configured.cert_store_stats()["x509_ca"] == 0
    assert configured.verify_mode == ssl.CERT_REQUIRED
    assert configured.check_hostname


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


@pytest.mark.parametrize("offline", [False, True])
def test_tracker_setup_prepares_gt_even_when_video_exists(
    tmp_path, monkeypatch, offline
):
    from motion_tracking.datasets import workflow

    directory = tmp_path / "data/tracker"
    video = directory / "inputs/17.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"preserved video")
    before = video.stat().st_mtime_ns
    reference = directory / "reference"
    reference.mkdir()
    key = "data/tracker/inputs/17.mp4"
    (reference / "input_integrity.json").write_text(
        json.dumps([dict(path=key, sha256=sha256(video))])
    )
    source = tmp_path / "I_IL_02.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("I_IL_02-GT/I_IL_02-GT_1.png", b"ground truth")
    recipe = dict(
        file=source.name, url=source.as_uri(), local_file=key, sha256=sha256(source)
    )
    if offline:
        cached = directory / "raw/lasiesta" / source.name
        cached.parent.mkdir(parents=True)
        cached.write_bytes(source.read_bytes())
    monkeypatch.setattr(tracker, "ROOT", tmp_path)
    monkeypatch.setattr(tracker, "TRACKER", directory)
    monkeypatch.setattr(workflow, "ROOT", tmp_path)
    monkeypatch.setattr(
        tracker, "records", lambda name: [recipe] if name == "lasiesta" else []
    )

    workflow.setup(purpose="tracker", offline=offline)

    gt = directory / "raw/lasiesta/I_IL_02-GT/I_IL_02-GT_1.png"
    assert gt.read_bytes() == b"ground truth"
    assert video.read_bytes() == b"preserved video"
    assert video.stat().st_mtime_ns == before
    gt.write_bytes(b"damaged")
    workflow.setup(purpose="tracker", offline=True)
    assert gt.read_bytes() == b"ground truth"
    assert video.stat().st_mtime_ns == before


def test_tracker_paths_do_not_depend_on_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert tracker_input(1) == ROOT / "data/tracker/inputs/01.mpg"
    assert tracker_input("19") == ROOT / "data/tracker/inputs/19.mp4"
    with pytest.raises(ValueError):
        tracker_input(20)


def test_detection_prepare_creates_only_placeholder_directories(tmp_path, monkeypatch):
    directory = tmp_path / "data/detection"
    monkeypatch.setattr(detection, "DETECTION", directory)

    detection.prepare()

    assert sorted(
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file()
    ) == ["inputs/.gitkeep", "raw/.gitkeep"]


def test_detection_setup_succeeds_without_manually_supplied_files(
    tmp_path, monkeypatch
):
    from motion_tracking.datasets import workflow

    directory = tmp_path / "data/detection"
    monkeypatch.setattr(detection, "DETECTION", directory)
    monkeypatch.setattr(workflow, "DETECTION", directory)
    monkeypatch.setattr(workflow, "ROOT", tmp_path)

    workflow.setup(purpose="detection")

    prepared = json.loads((directory / "generated/prepared.json").read_text())
    assert prepared == []


def test_detection_verify_explains_where_to_place_manual_inputs(tmp_path, monkeypatch):
    from motion_tracking.datasets import workflow

    directory = tmp_path / "data/detection"
    monkeypatch.setattr(detection, "DETECTION", directory)
    monkeypatch.setattr(workflow, "DETECTION", directory)
    monkeypatch.setattr(workflow, "ROOT", tmp_path)

    with pytest.raises(
        FileNotFoundError,
        match=r"manually.*raw/town_centre\.mp4.*inputs/target\.png",
    ):
        workflow.verify_data(purpose="detection")


def test_detection_verify_rejects_changed_manual_inputs(tmp_path, monkeypatch):
    directory = tmp_path / "data/detection"
    reference = directory / "reference"
    video = directory / "raw/town_centre.mp4"
    target = directory / "inputs/target.png"
    reference.mkdir(parents=True)
    video.parent.mkdir()
    target.parent.mkdir()
    video.write_bytes(b"video")
    target.write_bytes(b"target")
    record = {
        "path": "data/detection/raw/town_centre.mp4",
        "bytes": video.stat().st_size,
        "sha256": sha256(video),
        "target": {
            "path": "data/detection/inputs/target.png",
            "bytes": target.stat().st_size,
            "sha256": sha256(target),
        },
    }
    (reference / "source.json").write_text(json.dumps(record))
    monkeypatch.setattr(detection, "DETECTION", directory)

    detection.verify_inputs()
    target.write_bytes(b"change")

    with pytest.raises(ValueError, match="Checksum"):
        detection.verify_inputs()


@pytest.mark.parametrize("script", ["01_setup_data.py", "02_verify_data.py"])
def test_script_help_works_outside_repository(tmp_path, script):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_explicit_workspace_selects_data_for_installed_package(tmp_path, monkeypatch):
    from motion_tracking.datasets.paths import workspace_root

    monkeypatch.setenv("MOTION_TRACKING_ROOT", str(tmp_path))
    assert workspace_root() == tmp_path


def test_workflow_rejects_unknown_stage():
    from motion_tracking.datasets.workflow import main

    with pytest.raises(ValueError, match="Unknown workflow stage"):
        main("prepare")


def test_learning_rate_fails_before_output_without_raw_ground_truth(
    tmp_path, monkeypatch
):
    from motion_tracking.experiments import learning_rate

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
    from motion_tracking.datasets.media import convert_bmps

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
    from motion_tracking.datasets.workflow import check_video

    path = tmp_path / "short.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 25, (32, 24))
    writer.write(np.zeros((24, 32, 3), np.uint8))
    writer.release()
    with pytest.raises(ValueError, match="Incomplete"):
        check_video(path, 307)

"""Compact exports use memory and preserve previous results on failure."""

import csv
import json

import cv2
import numpy as np
import pytest

from experiments import storage


def test_compact_export_and_details_replacement(tmp_path):
    output = tmp_path / "output"
    for details in (True, False):
        with storage.result_directory(output, "matching") as staging:
            if details:
                (staging / "details").mkdir()
                (staging / "details/trace.json").write_text('[{"frame": 1}]')
            storage.publish_results(
                staging,
                "matching",
                [{"condition": "front", "matches": 3}],
                {"front": np.full((30, 40, 3), 120, np.uint8)},
                {"commit": "measured-revision"},
                details=details,
            )
        with (output / "summary.csv").open(encoding="utf-8-sig") as stream:
            assert list(csv.DictReader(stream)) == [
                {"condition": "front", "matches": "3"}
            ]
        metadata = json.loads((output / "metadata.json").read_text())
        assert metadata["commit"] == "measured-revision"
        assert metadata["experiment"] == "matching"
        assert cv2.imread(str(output / "comparison.jpg")) is not None
        assert (output / "details/trace.json").exists() == details
    assert {p.name for p in output.iterdir()} == {
        "summary.csv",
        "comparison.jpg",
        "metadata.json",
    }


def test_export_failure_preserves_previous_results(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    (output / "metadata.json").write_text('{"experiment": "matching"}')
    (output / "summary.csv").write_text("previous result")
    with pytest.raises(ValueError, match="images"):
        with storage.result_directory(output, "matching") as staging:
            storage.publish_results(staging, "matching", [{"matches": 3}], {}, {})
    assert (output / "summary.csv").read_text() == "previous result"
    assert list(tmp_path.iterdir()) == [output]


def test_export_refuses_unrelated_directory(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    (output / "notes.txt").write_text("keep")
    with pytest.raises(ValueError, match="output"):
        with storage.result_directory(output, "matching"):
            pytest.fail("Unrelated directory was accepted")
    assert (output / "notes.txt").read_text() == "keep"


def test_comparison_keeps_tall_observation_sheets_readable(tmp_path):
    output = tmp_path / "comparison.jpg"
    storage.comparison_image(
        {"observations": np.full((900, 300, 3), 120, np.uint8)}, output
    )
    image = cv2.imread(str(output))
    assert image.shape[0] > 2 * image.shape[1]


def test_matching_default_does_not_write_intermediate_files(tmp_path, monkeypatch):
    from pathlib import Path

    from experiments import feature_matching

    written = []
    original = Path.open

    def record_open(path, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            written.append(path.name)
        return original(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", record_open)
    original_imwrite = cv2.imwrite

    def record_image(path, image, *args):
        written.append(Path(path).name)
        return original_imwrite(path, image, *args)

    monkeypatch.setattr(cv2, "imwrite", record_image)

    # Default matching must not render detail-only images.
    def unexpected(*args, **kwargs):
        pytest.fail("Default matching rendered a detail image")

    monkeypatch.setattr(cv2, "drawKeypoints", unexpected)
    monkeypatch.setattr(cv2, "drawMatches", unexpected)
    feature_matching.main(["--output", str(tmp_path / "matching")])
    assert sorted(written) == [
        "comparison.jpg",
        "metadata.json",
        "roi-summary.csv",
        "summary.csv",
    ]


def test_matching_details_preserve_compact_measurements(tmp_path):
    from experiments import feature_matching

    compact, detailed = tmp_path / "compact", tmp_path / "detailed"
    feature_matching.main(["--output", str(compact)])
    feature_matching.main(["--details", "--output", str(detailed)])
    for name in ("summary.csv", "roi-summary.csv", "comparison.jpg"):
        assert (compact / name).read_bytes() == (detailed / name).read_bytes()
    assert not (compact / "details").exists()
    assert (detailed / "details/roi__keypoints__ORB_target.png").is_file()
    assert (detailed / "details/roi__matches__SIFT_front_0033.json").is_file()
    assert all(path.is_file() for path in (detailed / "details").iterdir())


def test_missing_tracking_video_cannot_publish_partial_summary(tmp_path, monkeypatch):
    from experiments import tracker_metrics

    # Other modules still point to the real dataset: validation must check the
    # declared tracker input root before starting any measurement.
    monkeypatch.setattr(tracker_metrics, "TRACKER", tmp_path / "missing-tracker")
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="Missing tracking inputs"):
        tracker_metrics.main(["--output", str(output)])
    assert not output.exists()

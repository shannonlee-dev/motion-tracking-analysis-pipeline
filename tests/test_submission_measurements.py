"""Protocol boundaries and equivalence to the actual application matcher."""

import csv
import json

import cv2
import pytest

from datasets.paths import RESULTS, TRACKER_REFERENCE
from experiments.tracker_metrics import associate, count_runs
from motion_tracking.matching import TargetMatcher

OUT = RESULTS / "tracker/baseline/submission"
MATCHER_OUT = RESULTS / "matcher/baseline/application"


def rows(identities, excluded=()):
    return [
        dict(frame=i, track_id=identity, excluded=i in excluded)
        for i, identity in enumerate(identities)
    ]


@pytest.mark.parametrize("length,expected", [(9, []), (10, [[0, 9]]), (21, [[0, 20]])])
def test_loss_is_one_event_per_ten_or_more_frame_run(length, expected):
    assert count_runs(rows([None] * length), None)[0] == expected


def test_occlusion_breaks_missing_runs():
    assert count_runs(rows([None] * 19, excluded=(9,)), None)[0] == []


@pytest.mark.parametrize("length,expected", [(4, 0), (5, 1), (20, 1)])
def test_switch_requires_five_consecutive_frames_after_overlap(length, expected):
    sequence = ["1"] * 5 + [None] * 3 + ["2"] * length
    assert len(count_runs(rows(sequence), [5, 7])[1]) == expected


def test_switch_preserves_pre_occlusion_identity_but_not_pending_streak():
    sequence = ["1"] * 5 + ["2"] * 4 + ["2"] * 5
    result = count_runs(rows(sequence, excluded=range(5, 9)), [5, 8])[1]
    assert result == [dict(start=9, confirmed=13, old="1", new="2")]


def test_non_overlap_id_changes_not_counted_as_overlap_switches():
    assert count_runs(rows(["1"] * 5 + ["2"] * 5), None)[1] == []


def test_one_detection_cannot_identify_two_people():
    assigned = associate(
        {"a": [0, 0, 20, 20], "b": [0, 0, 20, 20]}, {"7": [0, 0, 20, 20]}
    )
    assert list(assigned.values()).count("7") == 1


def test_recorded_feature_rows_equal_unmodified_app():
    recorded = list(
        csv.DictReader((MATCHER_OUT / "features.csv").open(encoding="utf-8-sig"))
    )
    matcher = TargetMatcher(cv2.imread("data/matcher/inputs/target.png"))
    selected = {int(row["frame"]): row for row in recorded}
    cap = cv2.VideoCapture("data/matcher/inputs/jogging.mp4")
    try:
        for index in range(max(selected) + 1):
            ok, frame = cap.read()
            assert ok
            if index in selected:
                result = matcher.match(frame)
                row = selected[index]
                for field in ("keypoints", "matches", "inliers"):
                    assert int(row[field]) == getattr(result, field)
                assert (row["found"] == "True") == result.found
                assert float(row["rate"]) == 100 * result.matches / len(
                    matcher.target_kp
                )
    finally:
        cap.release()


def test_every_summary_value_traces_to_event_rows():
    events = list(
        csv.DictReader((OUT / "event_results.csv").open(encoding="utf-8-sig"))
    )
    summaries = list(
        csv.DictReader((OUT / "tracking_summary.csv").open(encoding="utf-8-sig"))
    )
    specs = json.loads((TRACKER_REFERENCE / "events.json").read_text())
    assert len(specs) == 30 and len({e["event_id"] for e in specs}) == 30
    assert sorted(int(r["trials"]) for r in summaries if r["variant"] == "default") == [
        5,
        5,
        10,
        10,
    ]
    for summary in summaries:
        selected = [
            e
            for e in events
            if (e["variant"], e["condition"])
            == (summary["variant"], summary["condition"])
        ]
        assert len(selected) == int(summary["trials"])
        for field in ("id_switches", "failures"):
            assert sum(int(e[field]) for e in selected) == int(summary[field])
        assert 100 * sum(int(e["failed_event"]) for e in selected) / len(
            selected
        ) == float(summary["failure_rate"])

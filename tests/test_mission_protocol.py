import pytest
from motion_tracking.evaluation import count_post_overlap_switches


def test_temporary_overlap_change_is_not_post_overlap_switch():
    ids = [1]*10+[2]*10+[1]*10
    assert count_post_overlap_switches(ids, [False]*30, 10, 19) == 0


def test_overlap_change_persisting_after_separation_counts_once():
    ids = [1]*10+[2]*10+[2]*10
    assert count_post_overlap_switches(ids, [False]*30, 10, 19) == 1


def test_pre_overlap_fragmentation_is_baseline_not_event_and_four_frames_do_not_count():
    ids = [1]*5+[3]*5+[2]*10+[4]*4+[3]*6
    assert count_post_overlap_switches(ids, [False]*30, 10, 19) == 0


def test_exclusion_breaks_confirmation():
    ids = [1]*10+[2]*10+[4]*10
    excluded = [False]*30
    excluded[24] = excluded[29] = True
    assert count_post_overlap_switches(ids, excluded, 10, 19) == 0
    with pytest.raises(ValueError):
        count_post_overlap_switches(ids, excluded, 20, 10)

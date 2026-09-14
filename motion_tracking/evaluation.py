"""Event metrics, independent of tracker identity and prediction internals."""
import numpy as np
from motion_tracking.geometry import iou  # Re-export for existing callers.

IDENTITY_CONFIRMATION_FRAMES = 5
MISSING_FAILURE_FRAMES = 10
DEFAULT_MIN_IOU = 0.1
OCCLUSION_EXCLUSION_FRACTION = 0.5


def count_post_overlap_switches(assignments, excluded, start, end):
    """Compare post-separation IDs with the last confirmed pre-overlap ID.

    start/end are inclusive sequence indices of one physical overlap event.
    Changes before or inside overlap are not counted; later confirmed changes
    up to the end of the trial are counted, including fragmentation.
    """
    if len(assignments) != len(excluded) or not 0 <= start <= end < len(assignments):
        raise ValueError('Invalid overlap interval')
    before = count_events(assignments[:start], excluded[:start])['id_switches']
    masked = [skip or start <= i <= end for i, skip in enumerate(excluded)]
    return count_events(assignments, masked)['id_switches'] - before


def count_events(assignments, excluded):
    """Count confirmed ID changes (5 consecutive frames), misses (10).

    A missing run counts once, not once per frame. >=50% occlusion breaks
    pending runs but preserves the last confirmed identity across occlusion.
    Initial identity also needs five frames. Counts include fragmentation;
    they do not prove that a changed ID belongs to another physical object.
    """
    if len(assignments) != len(excluded):
        raise ValueError('Assignments and exclusion mask lengths differ')
    stable, pending, pending_length, miss_length = None, None, 0, 0
    switches, failures, missing_frames, eligible = 0, 0, 0, 0
    for identity, skip in zip(assignments, excluded):
        if skip:
            pending, pending_length, miss_length = None, 0, 0
            continue
        eligible += 1
        if identity is None:
            missing_frames += 1
            miss_length += 1
            pending, pending_length = None, 0
            if miss_length == MISSING_FAILURE_FRAMES:
                failures += 1
            continue
        miss_length = 0
        if identity == stable:
            pending, pending_length = None, 0
        else:
            pending_length = pending_length+1 if identity == pending else 1
            pending = identity
            if pending_length == IDENTITY_CONFIRMATION_FRAMES:
                switches += int(stable is not None)
                stable = identity
                pending, pending_length = None, 0
    return dict(id_switches=switches, failures=failures, missing_frames=missing_frames,
                eligible_frames=eligible, excluded_frames=sum(excluded))


def assign_ground_truth(truth, tracks, min_iou=DEFAULT_MIN_IOU):
    """One-to-one IoU matching of observed boxes; stale tracks cannot mask loss."""
    ids = list(truth)
    observed = [(tid, t) for tid, t in tracks.items() if t.missing == 0]
    result = {tid: None for tid in ids}
    if not ids or not observed:
        return result
    scores = np.array([[iou(truth[tid], t.bbox) for _, t in observed] for tid in ids])
    used_gt, used_pred = set(), set()
    for flat in np.argsort(-scores, axis=None, kind='stable'):
        row, col = np.unravel_index(flat, scores.shape)
        if scores[row, col] < min_iou:
            break
        if row not in used_gt and col not in used_pred:
            result[ids[row]] = observed[col][0]
            used_gt.add(row)
            used_pred.add(col)
    return result

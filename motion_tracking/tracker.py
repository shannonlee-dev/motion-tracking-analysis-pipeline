"""Greedy global nearest-centroid tracking. No appearance or learned features."""
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
import numpy as np
from motion_tracking.config import DEFAULT_CONFIG
from motion_tracking.geometry import BBox


@dataclass
class Track:
    bbox: BBox
    center: np.ndarray
    trail: deque[tuple[int, int]]
    missing: int = 0
    velocity: np.ndarray | None = None


class Tracker:
    def __init__(self, max_distance: float = DEFAULT_CONFIG.max_distance,
                 max_missing: int = DEFAULT_CONFIG.max_missing, trail_length: int = DEFAULT_CONFIG.trail_length,
                 predict_velocity: bool = DEFAULT_CONFIG.predict_velocity) -> None:
        if max_distance <= 0 or max_missing < 0 or trail_length < 1:
            raise ValueError('Invalid tracker limits')
        self.max_distance = max_distance
        self.max_missing = max_missing
        self.trail_length = trail_length
        self.predict_velocity = predict_velocity
        self.tracks: dict[int, Track] = {}
        self.next_id = 1

    def update(self, boxes: Iterable[BBox]) -> dict[int, Track]:
        boxes = [tuple(map(int, box)) for box in boxes]
        centers = np.array([(x+w/2, y+h/2) for x, y, w, h in boxes], dtype=float).reshape(-1, 2)
        ids = list(self.tracks)
        used_rows, used_cols = set(), set()
        if ids and boxes:
            positions = []
            for tid in ids:
                track = self.tracks[tid]
                offset = track.velocity * (track.missing+1) if self.predict_velocity else 0
                positions.append(track.center + offset)
            distances = np.linalg.norm(np.array(positions)[:, None, :] - centers[None, :, :], axis=2)
            for flat in np.argsort(distances, axis=None, kind='stable'):
                row, col = np.unravel_index(flat, distances.shape)
                if distances[row, col] > self.max_distance:
                    break
                if row in used_rows or col in used_cols:
                    continue
                track = self.tracks[ids[row]]
                track.velocity = (centers[col] - track.center) / (track.missing+1)
                track.center, track.bbox, track.missing = centers[col], boxes[col], 0
                track.trail.append(tuple(map(int, centers[col])))
                used_rows.add(row)
                used_cols.add(col)
        for row, tid in enumerate(ids):
            if row not in used_rows:
                self.tracks[tid].missing += 1
                if self.tracks[tid].missing > self.max_missing:
                    del self.tracks[tid]
        for col, box in enumerate(boxes):
            if col not in used_cols:
                trail = deque([tuple(map(int, centers[col]))], maxlen=self.trail_length)
                self.tracks[self.next_id] = Track(box, centers[col], trail, velocity=np.zeros(2))
                self.next_id += 1
        return self.tracks

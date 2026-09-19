"""전체 중심점 쌍 중 가까운 순서로 매칭하는 탐욕적 추적. 외형·학습 특징은 사용하지 않는다."""

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


class Tracker:
    def __init__(
        self,
        max_distance: float = DEFAULT_CONFIG.max_distance,
        max_missing: int = DEFAULT_CONFIG.max_missing,
        trail_length: int = DEFAULT_CONFIG.trail_length,
    ) -> None:
        if max_distance <= 0 or max_missing < 0 or trail_length < 1:
            raise ValueError("Invalid tracker limits")

        self.max_distance = max_distance
        self.max_missing = max_missing
        self.trail_length = trail_length
        self.tracks: dict[int, Track] = {}
        self.next_id = 1

    def update(self, boxes: Iterable[BBox]) -> dict[int, Track]:
        boxes = [tuple(map(int, box)) for box in boxes]
        # 검출 결과가 없어도 배열의 형태를 (0, 2)로 유지한다.
        centers = np.array(
            [(x + w / 2, y + h / 2) for x, y, w, h in boxes],
            dtype=float,
        ).reshape(-1, 2)
        ids = list(self.tracks)
        used_rows, used_cols = set(), set()

        if ids and boxes:
            positions = [self.tracks[tid].center for tid in ids]
            distances = np.linalg.norm(
                np.array(positions)[:, None, :] - centers[None, :, :],
                axis=2,
            )

            # 전체 쌍 중 가까운 순서로 매칭하며, 각 트랙과 검출 결과는 한 번만 사용한다.
            # 거리가 같으면 안정 정렬로 기존 행·열 순서를 유지한다.
            for flat in np.argsort(distances, axis=None, kind="stable"):
                row, col = np.unravel_index(flat, distances.shape)

                if distances[row, col] > self.max_distance:
                    break

                if row in used_rows or col in used_cols:
                    continue

                track = self.tracks[ids[row]]
                track.center, track.bbox, track.missing = centers[col], boxes[col], 0
                track.trail.append(tuple(map(int, centers[col])))
                used_rows.add(row)
                used_cols.add(col)

        # 매칭되지 않은 트랙은 연속 누락 프레임 수가 한도를 넘으면 삭제한다.
        for row, tid in enumerate(ids):
            if row not in used_rows:
                self.tracks[tid].missing += 1

                if self.tracks[tid].missing > self.max_missing:
                    del self.tracks[tid]

        # 매칭되지 않은 검출 결과마다 새 트랙을 생성한다.
        for col, box in enumerate(boxes):
            if col not in used_cols:
                trail = deque(
                    [tuple(map(int, centers[col]))],
                    maxlen=self.trail_length,
                )
                self.tracks[self.next_id] = Track(box, centers[col], trail)
                self.next_id += 1

        return self.tracks

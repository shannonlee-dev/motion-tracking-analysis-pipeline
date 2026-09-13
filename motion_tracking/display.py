"""Frame overlays and keyboard controls, shared by the app and evaluations."""
from pathlib import Path
import time
import cv2
import numpy as np


class Controls:
    def __init__(self):
        self.paused = False

    def handle(self, key, frame, snapshot_dir, frame_number):
        if key == ord('q'):
            return False
        if key == ord('p'):
            self.paused = not self.paused
        if key == ord('s') and frame is not None:
            directory = Path(snapshot_dir)
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / f'frame_{frame_number:06d}_{time.time_ns()}.png'
            if not cv2.imwrite(str(path), frame):
                raise OSError(f'Cannot save snapshot: {path}')
        return True


def draw_overlay(frame, tracks, fps, frame_number, match=None):
    image = frame.copy()
    for tid, track in tracks.items():
        if track.missing:
            continue  # Retained state is not an observed detection.
        color = (60+(tid*73)%190, 60+(tid*37)%190, 60+(tid*109)%190)
        x, y, w, h = track.bbox
        cv2.rectangle(image, (x, y), (x+w, y+h), color, 2)
        cv2.putText(image, f'ID:{tid}', (x, max(y-5, 15)), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1)
        cv2.circle(image, tuple(map(int, track.center)), 3, color, -1)
        if len(track.trail) > 1:
            cv2.polylines(image, [np.array(track.trail, np.int32)], False, color, 2)
    cv2.rectangle(image, (0, 0), (min(image.shape[1], 400), 24), (25, 25, 25), -1)
    cv2.putText(image, f'FPS: {fps:.1f} | frame {frame_number}', (7, 17),
                cv2.FONT_HERSHEY_SIMPLEX, .45, (255, 255, 255), 1)
    if match is not None and match.found:
        cv2.polylines(image, [match.polygon], True, (0, 255, 255), 2)
        cv2.putText(image, 'TARGET DETECTED', (7, 45), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 255), 2)
    return image

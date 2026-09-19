"""Overlay dimensions and clipping across low-resolution and 1080p inputs."""

import cv2
import numpy as np
import pytest

from motion_tracking.display import OverlayStyle, draw_overlay


@pytest.mark.parametrize("shape", [(120, 160), (288, 352), (1080, 1920)])
def test_overlay_is_visible_separated_and_does_not_mutate_input(shape, monkeypatch):
    frame = np.full((*shape, 3), 90, np.uint8)
    calls = []
    original = cv2.putText

    def capture(image, text, origin, font, scale, color, thickness, *args):
        calls.append((text, origin, scale, thickness))
        return original(image, text, origin, font, scale, color, thickness, *args)

    monkeypatch.setattr(cv2, "putText", capture)
    result = draw_overlay(frame, {}, 25, 5800)
    assert np.all(frame == 90)
    assert not np.array_equal(result, frame)
    assert calls[0][0].startswith("FPS:") and calls[1][0] == "Frame: 5800"
    assert calls[1][1][1] > calls[0][1][1]
    assert calls[0][2] >= 0.6
    if shape[0] == 1080:
        assert calls[0][2] >= 1.2 and calls[0][3] >= 2


def test_status_and_target_use_one_scaling_system():
    small = OverlayStyle.for_frame(np.zeros((288, 352, 3), np.uint8))
    large = OverlayStyle.for_frame(np.zeros((1080, 1920, 3), np.uint8))
    assert large.line_height > small.line_height
    assert large.padding > small.padding

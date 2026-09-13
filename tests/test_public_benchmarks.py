import numpy as np
import pytest
from scripts.eval.aloi import occlude
from scripts.data.lasiesta import labels as lasiesta_labels
from scripts.eval.lighting import confusion


def test_occlusion_counts_object_area_not_rectangle_area():
    mask = np.array([[0, 1, 0, 0], [1, 1, 1, 0], [0, 1, 1, 1]], dtype=bool)
    image = np.zeros((3, 4, 3), dtype=np.uint8)
    for fraction in (0, .3, .5, 1):
        result, count = occlude(image, mask, fraction)
        assert count == round(mask.sum()*fraction)
        assert np.count_nonzero((result[:, :, 0] == 127) & mask) == count
        assert abs(count/mask.sum()-fraction) <= .5/mask.sum()
    assert not image.any()
    with pytest.raises(ValueError):
        occlude(image, np.zeros_like(mask), .5)


def test_lasiesta_static_foreground_and_uncertain_exclusion():
    gt = np.array([[(0, 0, 0), (0, 0, 255), (255, 255, 255), (128, 128, 128)]], dtype=np.uint8)
    fg, valid = lasiesta_labels(gt)
    assert fg.tolist() == [[False, True, True, False]]
    assert confusion(np.array([[True, True, False, True]]), fg, valid) == (1, 1, 1, 0)

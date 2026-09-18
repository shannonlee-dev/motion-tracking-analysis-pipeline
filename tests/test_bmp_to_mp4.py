import cv2
import numpy as np
import pytest

from scripts.data.prepare_lasiesta import convert_bmps


def write_bmp(path, bgr):
    image = np.full((24, 32, 3), bgr, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)


def test_convert_bmps_uses_numeric_filename_order(tmp_path):
    frames = tmp_path / "frames"
    frames.mkdir()
    write_bmp(frames / "scene-10.bmp", (0, 0, 255))
    write_bmp(frames / "scene-2.bmp", (0, 255, 0))
    write_bmp(frames / "scene-1.bmp", (255, 0, 0))
    output = tmp_path / "sequence.mp4"

    count = convert_bmps(frames, output, fps=12)

    capture = cv2.VideoCapture(str(output))
    decoded = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        decoded.append(frame.mean(axis=(0, 1)))
    fps = capture.get(cv2.CAP_PROP_FPS)
    capture.release()

    assert count == 3
    assert len(decoded) == 3
    assert [int(color.argmax()) for color in decoded] == [0, 1, 2]
    assert fps == pytest.approx(12)


def test_convert_bmps_rejects_inconsistent_frame_sizes(tmp_path):
    frames = tmp_path / "frames"
    frames.mkdir()
    write_bmp(frames / "frame-1.bmp", (0, 0, 0))
    assert cv2.imwrite(
        str(frames / "frame-2.bmp"), np.zeros((12, 16, 3), dtype=np.uint8)
    )

    with pytest.raises(ValueError, match="frame size"):
        convert_bmps(frames, tmp_path / "sequence.mp4", fps=25)


def test_convert_bmps_rejects_empty_directory(tmp_path):
    with pytest.raises(ValueError, match="No BMP frames"):
        convert_bmps(tmp_path, tmp_path / "sequence.mp4", fps=25)

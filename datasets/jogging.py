"""Fixed Jogging selections and preparation; measurements live in evaluation.matcher."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from datasets.paths import MATCHER
from datasets.storage import atomic_bytes, download, extract, verify

INPUTS = MATCHER / "inputs"
SOURCE = MATCHER / "reference/Jogging"
ASSETS = MATCHER / "reference"
SELECTED_FRAMES = MATCHER / "generated/selected_frames"
TARGET_FRAME = 1
SCALE = 4
RATIO = 0.75
# Fixed after inspecting all 307 frames, before measuring matches.
SELECTIONS = [
    (
        "front",
        "정면",
        33,
        "얼굴과 상체 앞면이 보이는 비가림 프레임; target과 다른 시점",
    ),
    (
        "rotation_30",
        "약 30° 방향 변화",
        140,
        "얼굴·어깨가 초기 정면보다 오른쪽으로 향하는 약한 사선 자세",
    ),
    (
        "rotation_60",
        "약 60° 방향 변화",
        300,
        "얼굴 측면과 오른쪽을 향한 어깨가 보이는 더 큰 사선 자세",
    ),
    (
        "occlusion_30",
        "약 30% 가림",
        65,
        "전봇대 부착물이 몸의 오른쪽 일부를 가림; 얼굴과 왼쪽 몸은 보임",
    ),
    (
        "occlusion_50",
        "약 50% 가림",
        68,
        "전봇대와 부착물이 몸통·다리의 상당 부분을 가림",
    ),
]


def write_image(path: Path, image: np.ndarray) -> None:
    if not cv2.imwrite(str(path), image):
        raise OSError(f"Could not write {path}")


def crop(image: np.ndarray, bbox: np.ndarray) -> np.ndarray:
    """Convert OTB/MATLAB 1-based x,y to a 0-based half-open crop."""
    x, y, width, height = map(int, bbox)
    x, y = x - 1, y - 1
    if not (
        0 <= x < x + width <= image.shape[1] and 0 <= y < y + height <= image.shape[0]
    ):
        raise ValueError(f"Out-of-image GT: {bbox}")
    return image[y : y + height, x : x + width].copy()


def matching_image(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC)


def load_sequence() -> tuple[list[Path], np.ndarray, list[np.ndarray]]:
    paths = sorted((SOURCE / "img").glob("*.jpg"))
    gt = np.loadtxt(SOURCE / "groundtruth_rect.1.txt", dtype=int)
    if [p.name for p in paths] != [
        f"{n:04d}.jpg" for n in range(1, 308)
    ] or gt.shape != (307, 4):
        raise ValueError("Expected 307 Jogging frames and GT rows")
    images = [cv2.imread(str(p)) for p in paths]
    for number, (image, bbox) in enumerate(zip(images, gt), 1):
        if image is None or image.shape != (288, 352, 3):
            raise ValueError(f"Invalid Jogging frame {number}")
        crop(image, bbox)
    return paths, gt, images


def prepare(*, offline: bool = False) -> None:
    from datasets.paths import ROOT

    integrity = json.loads((ASSETS / "input_integrity.json").read_text())
    source_records = [r for r in integrity if "/reference/Jogging/" in r["path"]]
    if any(not (ROOT / r["path"]).exists() for r in source_records):
        record = json.loads((ASSETS / "sources.json").read_text())[0]
        archive = download(
            MATCHER / "raw/Jogging.zip", record["url"], record, offline=offline
        )
        extract(archive, ASSETS)
    for record in source_records:
        verify(ROOT / record["path"], record)
    paths, gt, images = load_sequence()
    INPUTS.mkdir(parents=True, exist_ok=True)
    target = INPUTS / "target.png"
    video = INPUTS / "jogging.mp4"
    if not target.exists():
        ok, encoded = cv2.imencode(".png", matching_image(crop(images[0], gt[0])))
        if not ok:
            raise OSError("Cannot encode Jogging target")
        target_record = next(r for r in integrity if r["path"].endswith("/target.png"))
        if hashlib.sha256(encoded).hexdigest() != target_record["sha256"]:
            raise ValueError("Jogging target differs from the pinned reference")
        atomic_bytes(target, encoded.tobytes())
    if not video.exists():
        import tempfile

        with tempfile.TemporaryDirectory(dir=INPUTS) as temporary:
            candidate = Path(temporary) / "jogging.mp4"
            writer = cv2.VideoWriter(
                str(candidate), cv2.VideoWriter_fourcc(*"mp4v"), 25, (352, 288)
            )
            if not writer.isOpened():
                raise OSError("Cannot create Jogging video")
            try:
                for image in images:
                    writer.write(image)
            finally:
                writer.release()
            verify(
                candidate,
                next(r for r in integrity if r["path"].endswith("/jogging.mp4")),
            )
            candidate.replace(video)
    for record in integrity:
        verify(ROOT / record["path"], record)
    for slug, number in [("target", TARGET_FRAME)] + [(s[0], s[2]) for s in SELECTIONS]:
        path = SELECTED_FRAMES / f"{slug}_{number:04d}.jpg"
        content = paths[number - 1].read_bytes()
        if not path.exists() or path.read_bytes() != content:
            atomic_bytes(path, content)

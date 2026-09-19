"""Oxford Town Centre: local-only source and reproducible person registration."""

import json
import shutil
import subprocess
from pathlib import Path

import cv2

from datasets.paths import DETECTION, ROOT
from datasets.storage import atomic_bytes, verify


def prepare(*, offline: bool = False, source: Path | None = None) -> None:
    record = json.loads((DETECTION / "reference/source.json").read_text())
    video = ROOT / record["path"]
    if not video.exists():
        if source is not None:
            verify(source, record)
            atomic_bytes(video, source.read_bytes())
        elif offline:
            raise FileNotFoundError(
                f"Oxford source missing: {video}. Run setup with --detection-source /path/to/TownCentreXVID.mp4"
            )
        else:
            downloader = shutil.which("aria2c")
            if downloader is None:
                raise OSError(
                    "Oxford is distributed via BitTorrent. Install aria2c or use --detection-source /path/to/TownCentreXVID.mp4; see data/detection/NOTICE.md"
                )
            cache = DETECTION / "raw/download"
            cache.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    downloader,
                    "--seed-time=0",
                    "--bt-stop-timeout=120",
                    "--dir=" + str(cache),
                    record["torrent"],
                ],
                check=True,
            )
            candidates = list(cache.rglob(record["original_name"]))
            if len(candidates) != 1:
                raise FileNotFoundError(
                    "Oxford download did not contain the expected video"
                )
            verify(candidates[0], record)
            candidates[0].replace(video)
    verify(video, record)
    target_record = record["target"]
    target = ROOT / target_record["path"]
    if target.exists():
        verify(target, target_record)
        return
    cap = cv2.VideoCapture(str(video))
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_record["frame"])
        ok, frame = cap.read()
        if not ok:
            raise ValueError("Cannot decode Oxford registration frame")
        x, y, width, height = target_record["bbox_xywh"]
        image = frame[y : y + height, x : x + width]
        ok, encoded = cv2.imencode(".png", image)
        if not ok:
            raise OSError("Cannot encode Oxford target")
        import hashlib

        if hashlib.sha256(encoded).hexdigest() != target_record["sha256"]:
            raise ValueError("Oxford target differs from pinned registration image")
        atomic_bytes(target, encoded.tobytes())
    finally:
        cap.release()

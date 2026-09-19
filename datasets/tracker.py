"""Prepare tracker 01–19 without overwriting pinned experimental inputs."""

import json
import shutil
import tempfile
from pathlib import Path

import cv2

from datasets.media import convert_bmps
from datasets.paths import ROOT, TRACKER
from datasets.storage import download, extract, sha256, verify, write_json


def records(name: str) -> list[dict]:
    return json.loads(
        (TRACKER / "reference/manifests" / f"{name}_sources.json").read_text()
    )


def encode_clip(source: Path, output: Path, start: int, count: int, fps: float) -> None:
    """Reconstruct clip boundaries; original H.264 encoder settings were not recorded."""
    cap = cv2.VideoCapture(str(source))
    writer = None
    try:
        # Sequential decoding keeps MPEG frame selection independent of seek support.
        for index in range(start + count):
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f"Unexpected end of {source} at frame {index}")
            if index < start:
                continue
            if writer is None:
                height, width = frame.shape[:2]
                writer = cv2.VideoWriter(
                    str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
                )
                if not writer.isOpened():
                    raise OSError(f"Cannot create {output}")
            writer.write(frame)
    finally:
        cap.release()
        if writer is not None:
            writer.release()


def prepare(*, offline: bool = False, raw: bool = False) -> None:
    pinned = {
        r["path"]: r
        for r in json.loads((TRACKER / "reference/input_integrity.json").read_text())
    }
    generated_path = TRACKER / "generated/inputs.json"
    generated = (
        json.loads(generated_path.read_text()) if generated_path.exists() else {}
    )
    groups = [
        ("caviar", records("caviar")),
        ("overlap", records("overlap")),
        ("lighting", records("lighting")),
        ("lasiesta", records("lasiesta")),
    ]
    for group, sources in groups:
        for record in sources:
            output = ROOT / (
                record["local_file"] if "local_file" in record else record["file"]
            )
            key = str(output.relative_to(ROOT))
            if output.exists():
                verify(output, generated.get(key, pinned[key]))
                if not raw:
                    continue
            raw_dir = TRACKER / "raw" / ("caviar" if group == "overlap" else group)
            if group == "overlap":
                source = download(
                    raw_dir / record["source_file"],
                    record["source_url"],
                    dict(bytes=record["source_bytes"], sha256=record["source_sha256"]),
                    offline=offline,
                )
                download(
                    raw_dir / record["gt_file"],
                    record["gt_url"],
                    dict(sha256=record["gt_sha256"]),
                    offline=offline,
                )
            elif group == "lighting":
                source = download(
                    raw_dir / record["raw_file"],
                    record["source_url"],
                    dict(
                        bytes=record.get("source_bytes", record.get("bytes")),
                        sha256=record.get("source_sha256", record.get("sha256")),
                    ),
                    offline=offline,
                )
            else:
                source = download(
                    raw_dir / record["file"], record["url"], record, offline=offline
                )
            if group == "lasiesta":
                extract(source, raw_dir)
            if output.exists():
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
                candidate = Path(temporary) / output.name
                if group == "caviar" or (
                    group == "lighting" and source.suffix == ".mp4"
                ):
                    shutil.copyfile(source, candidate)
                elif group == "overlap":
                    encode_clip(
                        source,
                        candidate,
                        record["source_start_frame"],
                        record["frames"],
                        record["fps"],
                    )
                elif group == "lasiesta":
                    count = convert_bmps(
                        raw_dir / source.stem, candidate, record["fps"]
                    )
                    if count != record["frames"]:
                        raise ValueError(f"Unexpected frame count for {source}")
                else:
                    frame_dir = raw_dir / source.stem
                    extract(source, frame_dir)
                    count = convert_bmps(frame_dir, candidate, 5)
                    if count != 2715:
                        raise ValueError("Expected 2,715 Wallflower BMP frames")
                digest = sha256(candidate)
                if digest != pinned[key]["sha256"]:
                    # Never change published source hashes or baseline measurements.
                    generated[key] = dict(
                        bytes=candidate.stat().st_size,
                        sha256=digest,
                        baseline_sha256=pinned[key]["sha256"],
                        source_sha256=sha256(source),
                        codec="mp4v",
                        opencv=cv2.__version__,
                        note="Reconstructed media; encoder bytes differ from the historical input. Rerun measurements.",
                    )
                else:
                    generated.pop(key, None)
                candidate.replace(output)
            write_json(generated_path, generated)

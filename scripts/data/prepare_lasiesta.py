"""Prepare official public benchmarks; verify pinned source checksums."""

import hashlib
import json
import re
import tempfile
import urllib.request
from collections.abc import Mapping
from pathlib import Path

import cv2

from scripts.constants import (
    LASIESTA_MANIFEST,
    LASIESTA_RAW_DIR,
    ROOT,
)

DOWNLOAD_TIMEOUT_SECONDS = 120


def natural_key(path: Path) -> list[object]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    ]


def convert_bmps(input_dir: Path, output: Path, fps: float = 25) -> int:
    """Write numerically ordered BMP frames from input_dir to an MP4."""
    input_dir = Path(input_dir)
    output = Path(output)
    frames = sorted(
        (
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".bmp"
        ),
        key=natural_key,
    ) if input_dir.is_dir() else []

    if not frames:
        raise ValueError(f"No BMP frames found in {input_dir}")
    if fps <= 0:
        raise ValueError("fps must be greater than zero")

    first = cv2.imread(str(frames[0]))
    if first is None:
        raise ValueError(f"Could not read BMP frame: {frames[0]}")

    height, width = first.shape[:2]
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(
        prefix=f".{output.stem}-", suffix=".mp4", dir=output.parent, delete=False
    )
    temporary_path = Path(temporary.name)
    temporary.close()
    writer = cv2.VideoWriter(
        str(temporary_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )

    if not writer.isOpened():
        temporary_path.unlink(missing_ok=True)
        raise OSError(f"Could not create MP4: {output}")

    try:
        for path in frames:
            frame = cv2.imread(str(path))
            if frame is None:
                raise ValueError(f"Could not read BMP frame: {path}")
            if frame.shape[:2] != (height, width):
                raise ValueError(
                    f"Inconsistent frame size: {path} is "
                    f"{frame.shape[1]}x{frame.shape[0]}, expected {width}x{height}"
                )
            writer.write(frame)
    except Exception:
        writer.release()
        temporary_path.unlink(missing_ok=True)
        raise

    writer.release()
    temporary_path.replace(output)
    return len(frames)


def verify(content: bytes, record: Mapping[str, object]) -> None:
    if (
        len(content) != record["bytes"]
        or hashlib.sha256(content).hexdigest() != record["sha256"]
    ):
        raise ValueError(f"Source checksum mismatch: {record['file']}")


def download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        return response.read()


def safe_path(root: Path, name: str) -> Path:
    path = Path(name)

    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Unsafe archive path")

    return root / path


def main() -> None:
    import libarchive  # optional preparation dependency; also needs OS libarchive

    destination = ROOT / LASIESTA_RAW_DIR
    destination.mkdir(parents=True, exist_ok=True)

    for rec in json.loads((ROOT / LASIESTA_MANIFEST).read_text()):
        path = destination / rec["file"]

        if not path.exists():
            content = download(rec["url"])
            verify(content, rec)
            path.write_bytes(content)

        verify(path.read_bytes(), rec)

        with libarchive.file_reader(str(path)) as archive:
            for entry in archive:
                out = safe_path(destination, entry.pathname)

                if entry.isdir:
                    out.mkdir(parents=True, exist_ok=True)
                elif entry.isfile:
                    out.parent.mkdir(parents=True, exist_ok=True)

                    with out.open("wb") as handle:
                        for block in entry.get_blocks():
                            handle.write(block)
                else:
                    raise ValueError("Unexpected archive entry type")

        output = ROOT / rec["local_file"]
        frame_dir = destination / Path(rec["file"]).stem
        frame_count = convert_bmps(frame_dir, output, fps=rec["fps"])
        if frame_count != rec["frames"]:
            raise ValueError(
                f"Unexpected frame count for {rec['file']}: "
                f"{frame_count}, expected {rec['frames']}"
            )
        output_bytes = output.read_bytes()
        if (
            len(output_bytes) != rec["output_bytes"]
            or hashlib.sha256(output_bytes).hexdigest() != rec["output_sha256"]
        ):
            raise ValueError(f"Generated MP4 checksum mismatch: {output}")


if __name__ == "__main__":
    main()

"""Convert a directory of numerically named BMP frames to MP4.

Run: python -m scripts.bmp_to_mp4 INPUT_DIR OUTPUT.mp4 [--fps 25]
"""

import argparse
from pathlib import Path
import re
import tempfile

import cv2


def natural_key(path: Path) -> list[object]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    ]


def convert_bmps(input_dir: Path, output: Path, fps: float = 25) -> int:
    """Write BMP frames from input_dir to output and return the frame count."""
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path, help="Directory containing BMP frames")
    parser.add_argument("output", type=Path, help="Output MP4 path")
    parser.add_argument("--fps", type=float, default=25, help="Playback FPS (default: 25)")
    args = parser.parse_args()

    try:
        count = convert_bmps(args.input_dir, args.output, args.fps)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"Wrote {count} frames to {args.output}")


if __name__ == "__main__":
    main()

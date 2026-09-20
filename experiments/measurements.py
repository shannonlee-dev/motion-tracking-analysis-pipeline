"""Collect measurements from the same runner used by the application CLI."""

import json
from dataclasses import replace
from pathlib import Path

from datasets.jogging import SELECTIONS, write_image
from datasets.paths import MATCHER
from experiments.storage import initialize_reproducibility, write_csv
from motion_tracking import runner
from motion_tracking.config import DEFAULT_CONFIG


def measure_application_matcher(details: Path | None = None):
    initialize_reproducibility()
    selected = {s[2] - 1: s for s in SELECTIONS}
    rows, images = [], {}

    def collect(result: runner.FrameResult):
        index = result.frame_number
        if index not in selected:
            return
        slug, label, source, _ = selected[index]
        match = result.match
        rows.append(
            dict(
                condition=label.replace("° 방향 변화", "도 회전"),
                video="data/matcher/inputs/jogging.mp4",
                frame=index,
                source_jpg_frame=source,
                keypoints=match.keypoints,
                matches=match.matches,
                target_keypoints=result.target_keypoints,
                rate=100 * match.matches / result.target_keypoints,
                inliers=match.inliers,
                found=match.found,
            )
        )
        images[f"feature_{slug}"] = result.frame.copy()
        if details is not None:
            write_image(details / f"application__feature_{slug}.png", result.frame)

    stats = runner.run(
        MATCHER / "inputs/jogging.mp4",
        target=MATCHER / "inputs/target.png",
        headless=True,
        on_frame=collect,
    )
    if stats["frames"] != 307 or len(rows) != len(selected):
        raise ValueError(
            f"Incomplete Jogging input: {stats['frames']} frames, {len(rows)} conditions"
        )
    rows.sort(key=lambda r: list(selected).index(r["frame"]))
    if details is not None:
        write_csv(details / "application__features.csv", rows)
    return rows, images


def measure_tracks(inputs: list[Path], details: Path | None = None):
    """Run each supported app configuration; retain only one video's tracks."""
    initialize_reproducibility()
    variants = {
        "default": DEFAULT_CONFIG,
        "distance_80": replace(DEFAULT_CONFIG, max_distance=80),
        "missing_30": replace(DEFAULT_CONFIG, max_missing=30),
    }
    for path in inputs:
        records = {key: [] for key in variants}
        for key, config in variants.items():

            def collect(result: runner.FrameResult):
                records[key].append(
                    dict(
                        frame=result.frame_number,
                        tracks={
                            str(tid): list(track.bbox)
                            for tid, track in result.tracks.items()
                            if track.missing == 0
                        },
                    )
                )

            runner.run(path, config, headless=True, on_frame=collect)
        if details is not None:
            for key, record in records.items():
                (details / f"tracks_{path.stem}_{key}.json").write_text(
                    json.dumps(record, separators=(",", ":")) + "\n"
                )
        print(path, len(records["default"]), flush=True)
        yield path.stem, records

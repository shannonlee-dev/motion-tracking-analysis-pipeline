"""Pair saved app traces for review; no inference or tracking occurs here."""

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np

from motion_tracking.datasets.paths import TRACKER_REFERENCE, tracker_input
from motion_tracking.experiments.storage import write_csv


def read_rows(path):
    with path.open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    truth = json.loads((TRACKER_REFERENCE / "ground_truth.json").read_text())
    left = read_rows(args.baseline / "summary.csv")
    right = {r["video"]: r for r in read_rows(args.candidate / "summary.csv")}
    comparison, selections = [], {}
    for before in left:
        name = before["video"]
        after = right[name]
        row = dict(video=name, split=before["split"])
        for key in before:
            if key in ("video", "split"):
                continue
            row[key + "_before"] = before[key]
            row[key + "_after"] = after[key]
        comparison.append(row)
        a = {
            int(r["frame"]): r for r in read_rows(args.baseline / f"{name}_metrics.csv")
        }
        b = {
            int(r["frame"]): r
            for r in read_rows(args.candidate / f"{name}_metrics.csv")
        }
        # Fixed selection rules expose both improvements and regressions.
        selected = {}
        for key, direction in [
            ("duplicates", -1),
            ("merges", 1),
            ("misses", 1),
            ("complete", 1),
        ]:
            f = max(a, key=lambda f: direction * (float(b[f][key]) - float(a[f][key])))
            if direction * (float(b[f][key]) - float(a[f][key])) > 0:
                selected.setdefault(f, []).append(key)
        if not selected:
            selected[sorted(a)[len(a) // 2]] = ["midpoint; no changed extreme"]
        selections[name] = selected
        records = [
            json.loads((directory / f"{name}_tracks.json").read_text())
            for directory in (args.baseline, args.candidate)
        ]
        cap = cv2.VideoCapture(str(tracker_input(name)))
        panels = []
        try:
            for f, reasons in sorted(selected.items()):
                cap.set(cv2.CAP_PROP_POS_FRAMES, f)
                ok, frame = cap.read()
                if not ok:
                    raise ValueError(f"Cannot read {name} f{f}")
                tiles = []
                for label, traces in zip(("baseline", "candidate"), records):
                    tile = frame.copy()
                    for gid, box in truth[name].get(str(f), {}).items():
                        x, y, w, h = map(int, box)
                        cv2.rectangle(tile, (x, y), (x + w, y + h), (255, 255, 0), 1)
                    for tid, box in traces[f]["tracks"].items():
                        x, y, w, h = map(int, box)
                        cv2.rectangle(tile, (x, y), (x + w, y + h), (0, 255, 0), 1)
                        cv2.putText(tile, tid, (x, max(10, y)), 0, 0.4, (0, 255, 0), 1)
                    tile = cv2.resize(
                        tile, (480, round(tile.shape[0] * 480 / tile.shape[1]))
                    )
                    banner = np.full((40, tile.shape[1], 3), 245, np.uint8)
                    cv2.putText(
                        banner,
                        f"{name} f{f} {label}: {','.join(reasons)}",
                        (5, 25),
                        0,
                        0.5,
                        (0, 0, 0),
                        1,
                    )
                    tiles.append(np.vstack((banner, tile)))
                panels.append(np.hstack(tiles))
        finally:
            cap.release()
        if not cv2.imwrite(
            str(args.output / f"{name}_comparison.jpg"), np.vstack(panels)
        ):
            raise OSError("Cannot write comparison")
    write_csv(args.output / "comparison.csv", comparison)
    (args.output / "selection.json").write_text(json.dumps(selections, indent=2) + "\n")


if __name__ == "__main__":
    main()

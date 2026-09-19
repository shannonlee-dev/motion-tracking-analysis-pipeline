"""Render tracker event evidence used by the report."""

import json
from pathlib import Path

import cv2
import numpy as np

from datasets.paths import TRACKER, TRACKER_REFERENCE


def run(output: Path) -> None:
    events = json.loads((TRACKER_REFERENCE / "events.json").read_text())
    runs = {
        r["event_id"]: r
        for r in json.loads((output / "counted_runs.json").read_text())
        if r["variant"] == "default"
    }
    truth = json.loads((TRACKER_REFERENCE / "ground_truth.json").read_text())
    directory = output / "review"
    directory.mkdir(exist_ok=True)
    requested = {}
    for event in events:
        samples = set(map(int, np.linspace(event["start"], event["end"], 8)))
        for run in runs[event["event_id"]]["failures"]:
            samples.update((run["start"], run["start"] + 9, run["end"]))
        for run in runs[event["event_id"]]["switches"]:
            samples.update((run["start"], run["confirmed"]))
        for start, end in event["exclude"]:
            samples.update((start, end))
        requested[event["event_id"]] = sorted(samples)
    for name in sorted({e["video"] for e in events}):
        path = next((TRACKER / "inputs").glob(name + ".*"))
        relevant = [e for e in events if e["video"] == name]
        needed = set().union(*(set(requested[e["event_id"]]) for e in relevant))
        frames = {}
        cap = cv2.VideoCapture(str(path))
        index = 0
        while index <= max(needed):
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f"Unexpected end: {path}, frame {index}")
            if index in needed:
                frames[index] = frame
            index += 1
        cap.release()
        tracks = json.loads((output / f"tracks_{name}_default.json").read_text())
        for event in relevant:
            tiles = []
            for index in requested[event["event_id"]]:
                frame = frames[index].copy()
                for identity, box in tracks[index]["tracks"].items():
                    x, y, w, h = map(int, box)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
                    cv2.putText(frame, identity, (x, max(y, 9)), 0, 0.3, (0, 255, 0), 1)
                for identity, box in truth[name].get(str(index), {}).items():
                    if identity not in event["objects"]:
                        continue
                    x, y, w, h = map(int, box)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 1)
                    cv2.putText(
                        frame, "GT" + identity, (x, y + h), 0, 0.3, (255, 255, 0), 1
                    )
                frame = cv2.resize(frame, (352, 264))
                excluded = any(lo <= index <= hi for lo, hi in event["exclude"])
                cv2.putText(
                    frame,
                    f"{event['event_id']} {name} f{index}"
                    + (" EXCL?" if excluded else ""),
                    (4, 20),
                    0,
                    0.5,
                    (0, 0, 255) if excluded else (0, 255, 255),
                    1,
                )
                tiles.append(frame)
            while len(tiles) % 4:
                tiles.append(np.zeros_like(tiles[0]))
            sheet = np.vstack(
                [np.hstack(tiles[i : i + 4]) for i in range(0, len(tiles), 4)]
            )
            if not cv2.imwrite(str(directory / f"{event['event_id']}.jpg"), sheet):
                raise OSError("Cannot write review image")
    print("Rendered 30 event review sheets")

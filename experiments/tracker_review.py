"""Render tracker event evidence used by the report."""

from pathlib import Path

import cv2
import numpy as np

from datasets.paths import TRACKER


def render_review(name, tracks, events, truth, counted, details: Path | None = None):
    """Render one video's evidence from in-memory tracks and event counts."""
    runs = {r["event_id"]: r for r in counted if r["variant"] == "default"}
    images = {}
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
    path = next((TRACKER / "inputs").glob(name + ".*"))
    needed = set().union(*(set(requested[e["event_id"]]) for e in events))
    frames = {}
    cap = cv2.VideoCapture(str(path))
    index = 0
    try:
        while index <= max(needed):
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f"Unexpected end: {path}, frame {index}")
            if index in needed:
                frames[index] = frame
            index += 1
    finally:
        cap.release()
    for event in events:
        tiles = []
        for index in requested[event["event_id"]]:
            frame = frames[index].copy()
            for identity, box in tracks[index]["tracks"].items():
                x, y, w, h = map(int, box)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
                cv2.putText(frame, identity, (x, max(y, 9)), 0, 0.3, (0, 255, 0), 1)
            for identity, box in truth.get(str(index), {}).items():
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
                f"{event['event_id']} {name} f{index}" + (" EXCL?" if excluded else ""),
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
        if details is not None:
            if not cv2.imwrite(
                str(details / f"review__{event['event_id']}.jpg"), sheet
            ):
                raise OSError("Cannot write review image")
        # Keep only a comparison-size sheet after each event, not all full sheets.
        height = max(1, round(sheet.shape[0] * 480 / sheet.shape[1]))
        images[event["event_id"]] = cv2.resize(sheet, (480, height))
    return images

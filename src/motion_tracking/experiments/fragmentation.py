"""Evaluate the real app; contains no foreground detector or tracker.

All boxes are measured, including unmatched fragments. GT bbox coverage is a
proxy for body extent, not pixel segmentation accuracy. Overlapping GT can make
merge candidates ambiguous; review the paired images as well.
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from statistics import median

import cv2
import numpy as np

from motion_tracking.config import Config
from motion_tracking.datasets.paths import TRACKER_REFERENCE, tracker_input
from motion_tracking.experiments.storage import (
    environment,
    initialize_reproducibility,
    write_csv,
)
from motion_tracking.runner import run

# Freeze at video level before experimenting. No adjacent-frame holdout.
DEVELOPMENT = {"02", "10", "18"}


def intersection(a, b):
    x, y, w, h = a
    X, Y, W, H = b
    return max(0, min(x + w, X + W) - max(x, X)) * max(0, min(y + h, Y + H) - max(y, Y))


def quality(truth, tracks):
    links = {g: [] for g in truth}
    merges, unmatched = 0, 0
    pairs = []
    coverage = {g: 0.0 for g in truth}
    for tid, pred in tracks.items():
        pa = max(1, pred[2] * pred[3])
        touched = []
        for gid, gt in truth.items():
            area = intersection(gt, pred)
            cov, purity = area / max(1, gt[2] * gt[3]), area / pa
            # Count even small leftover pieces when mostly inside a person.
            if cov >= 0.05 and purity >= 0.5:
                links[gid].append(tid)
            if cov >= 0.5:
                touched.append(gid)
            coverage[gid] = max(coverage[gid], cov if purity >= 0.5 else 0)
            if cov >= 0.7 and purity >= 0.5:
                pairs.append((cov * purity, gid, tid))
        merges += len(touched) > 1
        unmatched += not any(tid in v for v in links.values())
    assigned, used = {}, set()
    for _, gid, tid in sorted(pairs, reverse=True):
        if gid not in assigned and tid not in used:
            assigned[gid] = tid
            used.add(tid)
    return dict(
        people=len(truth),
        predictions=len(tracks),
        complete=len(assigned),
        misses=sum(not v for v in links.values()),
        duplicates=sum(max(0, len(v) - 1) for v in links.values()),
        fragmented=sum(len(v) > 1 for v in links.values()),
        merges=merges,
        unmatched=unmatched,
        coverage_sum=sum(coverage.values()),
        assigned=assigned,
    )


def component_count(mask):
    # Diagnostic only: number of raw connected regions, never used by the app.
    return cv2.connectedComponents((mask != 0).astype(np.uint8), connectivity=8)[0] - 1


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--videos", nargs="+", default=None)
    parser.add_argument("--config", default="{}", help="JSON Config overrides")
    parser.add_argument(
        "--manual-source", type=Path, help="GT-free video: qualitative only"
    )
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--speed-repeats", type=int, default=3)
    args = parser.parse_args()
    if args.speed_repeats < 1:
        parser.error("--speed-repeats must be positive")
    args.output.mkdir(parents=True, exist_ok=False)
    initialize_reproducibility()
    config = Config(**json.loads(args.config))
    truth = json.loads((TRACKER_REFERENCE / "ground_truth.json").read_text())
    events = json.loads((TRACKER_REFERENCE / "events.json").read_text())
    names = args.videos or sorted(truth)
    inputs = [tracker_input(name) for name in names]
    if args.manual_source:
        names, inputs = [args.manual_source.stem], [args.manual_source.resolve()]
    meta = environment(
        inputs
        + [TRACKER_REFERENCE / "ground_truth.json", TRACKER_REFERENCE / "events.json"]
    )
    meta.update(
        config=asdict(config),
        development=sorted(DEVELOPMENT),
        videos=names,
        max_frames=args.max_frames,
        speed_repeats=args.speed_repeats,
    )
    (args.output / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    summary = []
    event_rows, manual_rows = [], []
    for name, source in zip(names, inputs):
        rows, diagnostics, traces, images = [], [], [], []
        samples = {
            int((e["start"] + e["end"]) / 2) for e in events if e["video"] == name
        }
        if name not in truth:
            samples = {50, 100, 200, 299}
        previous = {}

        def observe(r):
            f = r.frame_number
            active = {tid: t.bbox for tid, t in r.tracks.items() if t.missing == 0}
            traces.append(
                dict(
                    frame=f, components=r.component_boxes, boxes=r.boxes, tracks=active
                )
            )
            gt = truth.get(name, {}).get(str(f))
            if f >= config.warmup_frames and gt is not None:
                q = quality(gt, active)
                assigned = q.pop("assigned")
                q["switches"] = sum(
                    g in previous and previous[g] != tid for g, tid in assigned.items()
                )
                previous.update(assigned)
                rows.append(dict(frame=f, **q))
            if f >= config.warmup_frames:
                diagnostics.append(
                    dict(
                        frame=f,
                        raw_components=component_count(r.raw_mask),
                        binary_components=component_count(r.binary_mask),
                        opened_components=component_count(r.opened_mask),
                        final_components=component_count(r.mask),
                        foreground_pixels=int(np.sum(r.raw_mask == 255)),
                        shadow_pixels=int(np.sum(r.raw_mask == 127)),
                        open_lost_pixels=int(
                            np.sum((r.binary_mask != 0) & (r.opened_mask == 0))
                        ),
                        component_boxes=len(r.component_boxes),
                        boxes=len(r.boxes),
                        tracks=len(active),
                    )
                )
            if f in samples:
                tiles = []
                for label, src in [
                    ("tracks", r.frame),
                    ("MOG2", r.raw_mask),
                    ("binary", r.binary_mask),
                    ("open", r.opened_mask),
                    ("final", r.mask),
                ]:
                    tile = (
                        src.copy()
                        if src.ndim == 3
                        else cv2.cvtColor(src, cv2.COLOR_GRAY2BGR)
                    )
                    if label == "tracks":
                        for gid, b in (gt or {}).items():
                            x, y, w, h = map(int, b)
                            cv2.rectangle(
                                tile, (x, y), (x + w, y + h), (255, 255, 0), 1
                            )
                        for tid, b in active.items():
                            x, y, w, h = b
                            cv2.rectangle(tile, (x, y), (x + w, y + h), (0, 255, 0), 1)
                            cv2.putText(
                                tile, str(tid), (x, max(10, y)), 0, 0.35, (0, 255, 0), 1
                            )
                    tile = cv2.resize(tile, (320, 240))
                    cv2.putText(
                        tile, f"{name} f{f} {label}", (4, 15), 0, 0.45, (0, 0, 255), 1
                    )
                    tiles.append(tile)
                images.append(np.hstack(tiles))

        stats = run(
            source, config, headless=True, on_frame=observe, max_frames=args.max_frames
        )
        # A separate run excludes observer, diagnostics and visualization overhead.
        speeds = [
            run(source, config, headless=True, max_frames=args.max_frames)["fps"]
            for _ in range(args.speed_repeats)
        ]
        if rows:
            total = {k: sum(r[k] for r in rows) for k in rows[0] if k != "frame"}
            total.update(
                video=name,
                split="development" if name in DEVELOPMENT else "heldout",
                evaluated_frames=len(rows),
                decoded_frames=stats["frames"],
                fps=median(speeds),
                fps_min=min(speeds),
                fps_max=max(speeds),
            )
            summary.append(total)
            write_csv(args.output / f"{name}_metrics.csv", rows)
        else:
            manual_rows.append(
                dict(
                    video=name,
                    review="no GT; manual only",
                    decoded_frames=stats["frames"],
                    fps=median(speeds),
                )
            )
        if diagnostics:
            write_csv(args.output / f"{name}_stages.csv", diagnostics)
        for event in (e for e in events if e["video"] == name):
            counts, last = [], {}
            for trace in traces:
                f = trace["frame"]
                if not event["start"] <= f <= event["end"] or f < config.warmup_frames:
                    continue
                if any(lo <= f <= hi for lo, hi in event["exclude"]):
                    continue
                gt = truth.get(name, {}).get(str(f), {})
                gt = {g: b for g, b in gt.items() if g in event["objects"]}
                q = quality(gt, trace["tracks"])
                assigned = q.pop("assigned")
                q["switches"] = sum(
                    g in last and last[g] != tid for g, tid in assigned.items()
                )
                last.update(assigned)
                counts.append(q)
            if counts:
                event_rows.append(
                    dict(
                        video=name,
                        event=event["event_id"],
                        condition=event["condition"],
                        frames=len(counts),
                        **{k: sum(r[k] for r in counts) for k in counts[0]},
                    )
                )
        (args.output / f"{name}_tracks.json").write_text(json.dumps(traces) + "\n")
        if images:
            if not cv2.imwrite(
                str(args.output / f"{name}_stages.jpg"), np.vstack(images)
            ):
                raise OSError("Cannot save stage evidence")
        print(name, summary[-1] if rows else "manual review only", flush=True)
    if summary:
        write_csv(args.output / "summary.csv", summary)
    if event_rows:
        write_csv(args.output / "events.csv", event_rows)
    if manual_rows:
        write_csv(args.output / "manual.csv", manual_rows)


if __name__ == "__main__":
    main()

"""Reproduce tracker traces, event metrics, and report review images."""

import json

from datasets.paths import TRACKER, TRACKER_REFERENCE
from experiments.storage import write_csv


def iou(a, b):
    x, y, w, h = a
    X, Y, W, H = b
    area = max(0, min(x + w, X + W) - max(x, X)) * max(0, min(y + h, Y + H) - max(y, Y))
    return area / max(w * h + W * H - area, 1)


def associate(truth, tracks):
    assigned = dict.fromkeys(truth)
    used = set()
    pairs = sorted(
        (
            (iou(box, pred), gid, tid)
            for gid, box in truth.items()
            for tid, pred in tracks.items()
        ),
        key=lambda x: -x[0],
    )
    for score, gid, tid in pairs:
        if score < 0.1:
            break
        if assigned[gid] is None and tid not in used:
            assigned[gid] = tid
            used.add(tid)
    return assigned


def count_runs(rows, overlap):
    stable = pending = None
    pending_start = misses_start = None
    failures, switches = [], []
    previous = None
    for r in rows + [dict(frame=rows[-1]["frame"] + 1, excluded=True, track_id=None)]:
        f, identity = r["frame"], r["track_id"]
        if r["excluded"] or identity is not None:
            if misses_start is not None and f - misses_start >= 10:
                failures.append([misses_start, f - 1])
            misses_start = None
        if r["excluded"]:
            pending = pending_start = None
            previous = f
            continue
        if identity is None:
            if misses_start is None:
                misses_start = f
            pending = pending_start = None
        elif overlap and overlap[0] <= f <= overlap[1]:
            pending = pending_start = None
        elif identity != stable:
            if pending != identity or previous != f - 1:
                pending, pending_start = identity, f
            if f - pending_start + 1 == 5:
                if stable is not None and overlap and f > overlap[1]:
                    switches.append(
                        dict(start=pending_start, confirmed=f, old=stable, new=identity)
                    )
                stable = identity
                pending = pending_start = None
        else:
            pending = pending_start = None
        previous = f
    return failures, switches


def evaluate(events, gt, records, *, keep_traces=False):
    all_results, traces, details = [], [], []
    for variant in ("default", "distance_80", "missing_30", "velocity"):
        for event in events:
            per_object = {g: [] for g in event["objects"]}
            for f in range(event["start"], event["end"] + 1):
                truth = gt[event["video"]].get(str(f), {})
                assigned = associate(truth, records[variant][f]["tracks"])
                occluded = any(lo <= f <= hi for lo, hi in event["exclude"])
                for gid in per_object:
                    row = dict(
                        event_id=event["event_id"],
                        variant=variant,
                        frame=f,
                        gt_id=gid,
                        track_id=assigned.get(gid),
                        excluded=occluded or gid not in truth or f < 25,
                        exclusion_reason="candidate_occlusion"
                        if occluded
                        else "absent_or_warmup"
                        if gid not in truth or f < 25
                        else "",
                    )
                    per_object[gid].append(row)
                    if keep_traces:
                        traces.append(row)
            failures, switches = [], []
            for gid, rows in per_object.items():
                loss, change = count_runs(rows, event["overlap"])
                failures += [dict(gt_id=gid, start=lo, end=hi) for lo, hi in loss]
                switches += [dict(gt_id=gid, **s) for s in change]
            details.append(
                dict(
                    event_id=event["event_id"],
                    variant=variant,
                    failures=failures,
                    switches=switches,
                )
            )
            all_results.append(
                dict(
                    event_id=event["event_id"],
                    variant=variant,
                    video=event["video"],
                    condition=event["condition"],
                    start=event["start"],
                    end=event["end"],
                    id_switches=len(switches),
                    failures=len(failures),
                    failed_event=int(bool(failures)),
                    note=event["note"],
                    excluded_intervals=json.dumps(event["exclude"]),
                )
            )
    return all_results, traces, details


def write_details(output, events, all_results, traces, details):
    event_log = []
    for event, result, counted in zip(
        events, all_results[: len(events)], details[: len(events)]
    ):
        loss = (
            "; ".join(
                f"GT{r['gt_id']} {r['start']}–{r['end']}" for r in counted["failures"]
            )
            or "없음"
        )
        changes = (
            "; ".join(
                f"GT{r['gt_id']} ID{r['old']}→{r['new']} {r['start']}–{r['confirmed']}"
                for r in counted["switches"]
            )
            or "없음"
        )
        suffix = ".mpg" if event["video"] in ("01", "02", "03") else ".mp4"
        event_log.append(
            {
                "영상명": event["video"] + suffix,
                "조건": event["condition"],
                "프레임 범위": f"{event['start']}–{event['end']}",
                "ID Switch 수": result["id_switches"]
                if event["overlap"]
                else "해당 없음",
                "실패 수": result["failures"],
                "관찰 메모": f"{event['event_id']}; GT {','.join(event['objects'])}; {event['note']}; 제외 후보 {json.dumps(event['exclude'])}; 누락 {loss}; ID 변경 {changes}",
            }
        )
    write_csv(output / "event_log.csv", event_log)
    write_csv(output / "event_results.csv", all_results)
    write_csv(output / "frame_assignments.csv", traces)
    (output / "counted_runs.json").write_text(
        json.dumps(details, ensure_ascii=False, indent=2) + "\n"
    )


def summarize(events, all_results):
    summary = []
    for variant in ("default", "distance_80", "missing_30", "velocity"):
        for condition in dict.fromkeys(e["condition"] for e in events):
            selected = [
                r
                for r in all_results
                if r["variant"] == variant and r["condition"] == condition
            ]
            summary.append(
                dict(
                    variant=variant,
                    condition=condition,
                    trials=len(selected),
                    id_switches=sum(r["id_switches"] for r in selected),
                    failures=sum(r["failures"] for r in selected),
                    failed_events=sum(r["failed_event"] for r in selected),
                    failure_rate=100
                    * sum(r["failed_event"] for r in selected)
                    / len(selected),
                )
            )
    return summary


def main(argv: list[str] | None = None) -> None:
    from experiments.measurements import measure_tracks
    from experiments.storage import (
        environment,
        initialize_reproducibility,
        publish_results,
        result_arguments,
        result_directory,
    )
    from experiments.tracker_review import render_review

    args = result_arguments("tracking", argv)
    initialize_reproducibility()
    events = json.loads((TRACKER_REFERENCE / "events.json").read_text())
    gt = json.loads((TRACKER_REFERENCE / "ground_truth.json").read_text())
    with result_directory(args.output, "tracking") as output:
        details = output / "details" if args.details else None
        if details is not None:
            details.mkdir()
        results, traces, counted, images = [], [], [], {}
        for name, records in measure_tracks(details):
            relevant = [event for event in events if event["video"] == name]
            measured, assigned, runs = evaluate(
                relevant, gt, records, keep_traces=args.details
            )
            results.extend(measured)
            if relevant:
                images.update(
                    render_review(
                        name, records["default"], relevant, gt[name], runs, details
                    )
                )
            if details is not None:
                traces.extend(assigned)
                counted.extend(runs)
            del records
        if details is not None:
            variants = ["default", "distance_80", "missing_30", "velocity"]
            order = {e["event_id"]: i for i, e in enumerate(events)}

            def key(row):
                return variants.index(row["variant"]), order[row["event_id"]]

            results.sort(key=key)
            counted.sort(key=key)
            traces.sort(
                key=key
            )  # Stable sort retains frame/object order within events.
            write_details(details, events, results, traces, counted)
        publish_results(
            output,
            "tracking",
            summarize(events, results),
            images,
            environment(sorted((TRACKER / "inputs").glob("*"))),
            details=args.details,
        )


if __name__ == "__main__":
    main()

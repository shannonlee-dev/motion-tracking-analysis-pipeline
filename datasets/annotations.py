"""Rebuild explicit tracker annotations from local dataset labels."""

import hashlib
import json
import xml.etree.ElementTree as E
from pathlib import Path

import cv2
import numpy as np

from datasets.paths import ROOT, TRACKER, TRACKER_REFERENCE
from datasets.storage import write_json


def parse(p: Path, offset: int = 0) -> dict[int, dict[str, list[float]]]:
    out = {}
    for f in E.parse(p).getroot().findall("frame"):
        boxes = {}
        for o in f.findall("objectlist/object"):
            b = o.find("box")
            v = {k: float(v) for k, v in b.attrib.items()}
            boxes[o.get("id")] = [
                v["xc"] - v["w"] / 2,
                v["yc"] - v["h"] / 2,
                v["w"],
                v["h"],
            ]
        out[int(f.get("number")) - offset] = boxes
    return out


def rebuild(output: Path) -> None:
    out = output
    out.mkdir(parents=True, exist_ok=True)
    truth = {}
    sources = []
    for n in ["01", "02", "03"]:
        p = TRACKER_REFERENCE / "annotations" / f"{n}.xml"
        truth[n] = parse(p)
        sources.append(
            dict(
                video=n,
                annotation=str(p.relative_to(ROOT)),
                sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                origin="Cached CAVIAR XML recovered from /tmp/mission-scene-audit; dataset name and visual alignment checked; not prior tracking results",
            )
        )
    for m in json.loads(
        (TRACKER_REFERENCE / "manifests/overlap_sources.json").read_text()
    ):
        n = Path(m["file"]).stem
        p = (TRACKER / "raw/caviar") / m["gt_file"]
        truth[n] = {
            f: b
            for f, b in parse(p, m["source_start_frame"]).items()
            if 0 <= f < m["frames"]
        }
        sources.append(
            dict(
                video=n,
                annotation=str(p.relative_to(ROOT)),
                sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                source_start=m["source_start_frame"],
            )
        )
    for n, seq in [
        ("15", "I_OC_01"),
        ("16", "I_OC_02"),
        ("17", "I_IL_02"),
        ("18", "I_IL_01"),
        ("19", "I_CA_01"),
    ]:
        truth[n] = {}
        for p in sorted((TRACKER / ("raw/lasiesta/" + seq + "-GT")).glob("*.png")):
            f = int(p.stem.split("_")[-1]) - 1
            im = cv2.imread(str(p))
            mask = np.all(im == (0, 0, 255), axis=2) | np.all(im == 255, axis=2)
            truth[n][f] = (
                {"1": list(cv2.boundingRect(mask.astype("uint8")))}
                if mask.any()
                else {}
            )
        sources.append(
            dict(
                video=n,
                annotation="data/tracker/raw/lasiesta/" + seq + "-GT",
                origin="Red foreground plus white temporarily static object; gray uncertainty ignored; bbox from label mask",
            )
        )
    anchors = json.loads(
        (TRACKER_REFERENCE / "annotations" / "14_anchors.json").read_text()
    )
    truth["14"] = {}
    for group in anchors:
        for (lo, a), (hi, b) in zip(group, group[1:]):
            for f in range(lo, hi + 1):
                truth["14"][f] = {
                    "1": (
                        np.array(a) + (np.array(b) - a) * (f - lo) / (hi - lo)
                    ).tolist()
                }
    sources.append(
        dict(
            video="14",
            origin="Manually observed bbox anchors in 160x120 original frames; interpolated; approximate association labels, not dataset GT",
            annotation="data/tracker/reference/annotations/14_anchors.json",
        )
    )
    write_json(out / "ground_truth.json", truth)
    write_json(out / "annotation_sources.json", sources)

"""Jogging ROI ORB/SIFT measurement, distinct from the app full-frame matcher."""

import csv
import json
from pathlib import Path

import cv2
import numpy as np

from datasets.jogging import (
    RATIO,
    SCALE,
    SELECTIONS,
    TARGET_FRAME,
    crop,
    load_sequence,
    matching_image,
    write_image,
)
from motion_tracking.features import unique_ratio_matches


def run(output: Path) -> list[dict]:
    cv2.setNumThreads(1)
    cv2.setRNGSeed(0)
    for directory in (output, output / "matches", output / "keypoints"):
        directory.mkdir(parents=True, exist_ok=True)
    paths, gt, images = load_sequence()
    target = crop(images[TARGET_FRAME - 1], gt[TARGET_FRAME - 1])
    crops = [crop(images[number - 1], gt[number - 1]) for _, _, number, _ in SELECTIONS]
    preview = []
    labels = [("target", TARGET_FRAME)] + [(s[0], s[2]) for s in SELECTIONS]
    for (label, number), roi in zip(labels, [target] + crops):
        enlarged = cv2.resize(roi, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
        tile = np.zeros((570, 180, 3), np.uint8)
        tile[35 : 35 + enlarged.shape[0], : enlarged.shape[1]] = enlarged
        cv2.putText(
            tile,
            f"{label} {number}",
            (3, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (255, 255, 255),
            1,
        )
        preview.append(tile)
    write_image(output / "selected_preview.png", np.hstack(preview))
    rows, settings = [], {}
    for algorithm, detector, norm in (
        ("ORB", cv2.ORB_create(nfeatures=1500), cv2.NORM_HAMMING),
        ("SIFT", cv2.SIFT_create(nfeatures=1500), cv2.NORM_L2),
    ):
        reference = matching_image(target)
        ref_kp, ref_desc = detector.detectAndCompute(reference, None)
        if ref_desc is None:
            raise ValueError(f"No {algorithm} descriptors in target")
        matcher = cv2.BFMatcher(norm, crossCheck=False)
        settings[algorithm] = dict(
            nfeatures=1500,
            other_parameters="OpenCV defaults",
            target_keypoints=len(ref_kp),
            norm="HAMMING" if algorithm == "ORB" else "L2",
        )
        write_image(
            output / "keypoints" / f"{algorithm}_target.png",
            cv2.drawKeypoints(reference, ref_kp, None, color=(0, 255, 0)),
        )
        for (slug, label, number, _), roi in zip(SELECTIONS, crops):
            scene = matching_image(roi)
            keypoints, descriptors = detector.detectAndCompute(scene, None)
            # Query = condition crop; reference = target. Deduplicate target indices.
            matches = (
                []
                if descriptors is None
                else unique_ratio_matches(matcher, descriptors, ref_desc, RATIO)
            )
            rate = 100 * len(matches) / len(ref_kp)
            rows.append(
                dict(
                    algorithm=algorithm,
                    condition=label,
                    frame=number,
                    extracted_keypoints=len(keypoints),
                    matched_keypoints=len(matches),
                    match_rate_percent=f"{rate:.2f}",
                    target_keypoints=len(ref_kp),
                )
            )
            write_image(
                output / "keypoints" / f"{algorithm}_{slug}.png",
                cv2.drawKeypoints(scene, keypoints, None, color=(0, 255, 0)),
            )
            drawn = cv2.drawMatches(
                scene,
                keypoints,
                reference,
                ref_kp,
                matches,
                None,
                matchColor=(0, 255, 0),
                singlePointColor=(0, 0, 255),
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
            )
            write_image(
                output / "matches" / f"{algorithm}_{slug}_{number:04d}.png", drawn
            )
            pairs = [
                dict(
                    condition_keypoint=m.queryIdx,
                    target_keypoint=m.trainIdx,
                    condition_xy=list(keypoints[m.queryIdx].pt),
                    target_xy=list(ref_kp[m.trainIdx].pt),
                    distance=m.distance,
                )
                for m in matches
            ]
            (output / "matches" / f"{algorithm}_{slug}_{number:04d}.json").write_text(
                json.dumps(pairs, indent=2) + "\n"
            )

    with (output / "metrics.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    settings.update(
        opencv=cv2.__version__,
        resize_scale=SCALE,
        interpolation="INTER_CUBIC",
        grayscale=True,
        ratio_test=RATIO,
        query="condition GT crop",
        train="target GT crop",
        uniqueness="best distance per target descriptor",
        geometric_verification=False,
        rate_denominator="target keypoints",
        video_playback_fps=25,
    )
    (output / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    return rows

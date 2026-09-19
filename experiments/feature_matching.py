"""Reproduce Jogging ROI and full-frame application matching separately."""

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
from datasets.paths import MATCHER
from experiments.storage import initialize_reproducibility, write_csv
from motion_tracking.features import unique_ratio_matches


def run(details: Path | None = None):
    initialize_reproducibility()
    _, gt, images = load_sequence()
    target = crop(images[TARGET_FRAME - 1], gt[TARGET_FRAME - 1])
    crops = [crop(images[number - 1], gt[number - 1]) for _, _, number, _ in SELECTIONS]
    if details is not None:
        preview = []
        labels = [("target", TARGET_FRAME)] + [(s[0], s[2]) for s in SELECTIONS]
        for (label, number), roi in zip(labels, [target] + crops):
            enlarged = cv2.resize(
                roi, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST
            )
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
        write_image(details / "roi__selected_preview.png", np.hstack(preview))
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
        if details is not None:
            write_image(
                details / f"roi__keypoints__{algorithm}_target.png",
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
            if details is not None:
                write_image(
                    details / f"roi__keypoints__{algorithm}_{slug}.png",
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
                    details / f"roi__matches__{algorithm}_{slug}_{number:04d}.png",
                    drawn,
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
                (
                    details / f"roi__matches__{algorithm}_{slug}_{number:04d}.json"
                ).write_text(json.dumps(pairs, indent=2) + "\n")

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
    if details is not None:
        write_csv(details / "roi__metrics.csv", rows)
        (details / "roi__settings.json").write_text(
            json.dumps(settings, indent=2) + "\n"
        )
    return rows, settings


def main(argv: list[str] | None = None) -> None:
    from experiments.measurements import measure_application_matcher
    from experiments.storage import (
        environment,
        publish_results,
        result_arguments,
        result_directory,
    )

    args = result_arguments("matching", argv)
    with result_directory(args.output, "matching") as output:
        details = output / "details" if args.details else None
        if details is not None:
            details.mkdir()
        roi_rows, settings = run(details)
        rows, images = measure_application_matcher(details)
        metadata = environment(
            [MATCHER / "inputs/jogging.mp4", MATCHER / "inputs/target.png"]
        )
        metadata["settings"] = {"roi/settings.json": settings}
        publish_results(
            output,
            "matching",
            rows,
            images,
            metadata,
            details=args.details,
            extra_summaries={"roi-summary.csv": roi_rows},
        )


if __name__ == "__main__":
    main()

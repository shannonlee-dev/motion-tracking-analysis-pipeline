"""Measure original-size BGR, grayscale, and grayscale x4 on fixed Jogging ROIs."""

import json
from pathlib import Path

import cv2

from datasets.jogging import (
    RATIO,
    SELECTIONS,
    SOURCE,
    TARGET_FRAME,
    crop,
    load_sequence,
)
from experiments.storage import environment, initialize_reproducibility, write_csv
from motion_tracking.features import unique_ratio_matches


def preprocess(image, variant):
    if variant == "original_bgr":
        return image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if variant == "gray_1x":
        return gray
    return cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)


def main():
    initialize_reproducibility()
    paths, gt, images = load_sequence()
    output = Path("docs/evidence/matching-preprocessing")
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for algorithm, detector, norm in (
        ("ORB", cv2.ORB_create(nfeatures=1500), cv2.NORM_HAMMING),
        ("SIFT", cv2.SIFT_create(nfeatures=1500), cv2.NORM_L2),
    ):
        for variant in ("original_bgr", "gray_1x", "gray_4x"):
            reference = preprocess(
                crop(images[TARGET_FRAME - 1], gt[TARGET_FRAME - 1]), variant
            )
            ref_kp, ref_desc = detector.detectAndCompute(reference, None)
            matcher = cv2.BFMatcher(norm, crossCheck=False)
            for _, condition, number, _ in SELECTIONS:
                scene = preprocess(crop(images[number - 1], gt[number - 1]), variant)
                keypoints, descriptors = detector.detectAndCompute(scene, None)
                matches = (
                    unique_ratio_matches(matcher, descriptors, ref_desc, RATIO)
                    if descriptors is not None and ref_desc is not None
                    else []
                )
                rows.append(
                    dict(
                        algorithm=algorithm,
                        variant=variant,
                        condition=condition,
                        frame=number,
                        extracted_keypoints=len(keypoints),
                        target_keypoints=len(ref_kp),
                        matched_keypoints=len(matches),
                        match_rate_percent=(
                            round(100 * len(matches) / len(ref_kp), 2)
                            if ref_kp
                            else None
                        ),
                        target_width=reference.shape[1],
                        target_height=reference.shape[0],
                    )
                )
    write_csv(output / "metrics.csv", rows)
    selected = [TARGET_FRAME] + [s[2] for s in SELECTIONS]
    metadata = environment(
        [paths[n - 1] for n in selected] + [SOURCE / "groundtruth_rect.1.txt"]
    )
    metadata["settings"] = dict(
        target_frame=TARGET_FRAME,
        frame_numbering="1-based original JPG",
        variants=["original_bgr", "gray_1x", "gray_4x"],
        preprocessing="GT crop; optional BGR2GRAY; optional INTER_CUBIC x4",
        zero_target_rate="undefined; blank CSV cell",
        nfeatures=1500,
        detector_other_parameters="OpenCV defaults",
        ratio_test=RATIO,
        query="condition GT crop",
        train="target GT crop",
        uniqueness="best distance per target descriptor",
        rate_denominator="target keypoints of each variant",
        geometric_verification=False,
    )
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()

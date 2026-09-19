"""Reproduce learning-rate masks and LASIESTA pixel metrics."""

from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

from datasets.paths import TRACKER
from experiments.storage import environment, initialize_reproducibility, write_csv
from motion_tracking.config import DEFAULT_CONFIG
from motion_tracking.motion import MotionDetector


def validate_inputs() -> None:
    video = TRACKER / "inputs/17.mp4"
    gt_directory = TRACKER / "raw/lasiesta/I_IL_02-GT"
    if not video.is_file() or not gt_directory.is_dir():
        raise ValueError(
            "Learning-rate ground truth is missing.\n"
            "Run:\n"
            "python scripts/01_setup_data.py --purpose tracker --raw"
        )
    gt_paths = sorted(gt_directory.glob("*.png"))
    if len(gt_paths) != 525:
        raise ValueError(
            "Learning-rate ground truth must contain exactly 525 frames; "
            f"found {len(gt_paths)}.\n"
            "Run:\n"
            "python scripts/01_setup_data.py --purpose tracker --raw"
        )
    for path in (gt_paths[0], gt_paths[-1]):
        if cv2.imread(str(path)) is None:
            raise ValueError(f"Cannot decode learning-rate ground truth: {path}")
    capture = cv2.VideoCapture(str(video))
    try:
        if not capture.isOpened():
            raise ValueError(f"Cannot open learning-rate video: {video}")
        count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if count != 525:
            raise ValueError(
                f"Learning-rate video must contain 525 frames; found {count}"
            )
    finally:
        capture.release()


def run(details: Path | None = None):
    summary, images = [], {}
    for rate in (0.001, 0.01, 0.1):
        cap = cv2.VideoCapture(str(TRACKER / "inputs/17.mp4"))
        detector = MotionDetector(replace(DEFAULT_CONFIG, learning_rate=rate))
        # An identical separate model exposes labels before threshold/morphology.
        raw_model = cv2.createBackgroundSubtractorMOG2(
            history=DEFAULT_CONFIG.history,
            varThreshold=DEFAULT_CONFIG.var_threshold,
            detectShadows=True,
        )
        rows, observations, tiles = [], [], []
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                index = len(rows)
                boxes, mask = detector.detect(frame)
                if details is not None:
                    observations.append(
                        dict(
                            frame=index,
                            foreground_pixels=int(np.count_nonzero(mask)),
                            foreground_fraction=float(np.mean(mask > 0)),
                            boxes=len(boxes),
                            mean_gray=float(
                                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()
                            ),
                        )
                    )
                if index in (100, 170, 190, 210, 240, 270, 300, 350, 420):
                    im = frame.copy()
                    for x, y, w, h in boxes:
                        cv2.rectangle(im, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    a = cv2.resize(im, (320, 240))
                    b = cv2.resize(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), (320, 240))
                    cv2.putText(
                        a, f"LR {rate} f{index}", (5, 20), 0, 0.6, (0, 255, 255), 1
                    )
                    tiles.append(np.hstack([a, b]))
                raw = raw_model.apply(frame, learningRate=rate)
                gt = cv2.imread(
                    str(TRACKER / f"raw/lasiesta/I_IL_02-GT/I_IL_02-GT_{index + 1}.png")
                )
                if gt is None or gt.shape != frame.shape:
                    raise ValueError(f"Missing or mismatched GT at {index}")
                foreground = np.all(gt == (0, 0, 255), axis=2) | np.all(
                    gt == 255, axis=2
                )
                background = np.all(gt == 0, axis=2)
                rows.append(
                    dict(
                        frame=index,
                        tp=int(((mask > 0) & foreground).sum()),
                        fg_pixels=int(foreground.sum()),
                        fp=int(((mask > 0) & background).sum()),
                        bg_pixels=int(background.sum()),
                        person_raw_background=int(((raw == 0) & foreground).sum()),
                        person_raw_shadow=int(((raw == 127) & foreground).sum()),
                        person_raw_foreground=int(((raw == 255) & foreground).sum()),
                    )
                )
        finally:
            cap.release()
        if len(rows) != 525:
            raise ValueError(f"Expected 525 frames, got {len(rows)}")
        image = np.vstack(tiles)
        images[f"learning_rate_{rate}"] = image
        if details is not None:
            write_csv(details / f"learning_rate_{rate}_gt.csv", rows)
            write_csv(details / f"learning_rate_{rate}.csv", observations)
            if not cv2.imwrite(str(details / f"learning_rate_{rate}.jpg"), image):
                raise OSError("Cannot write learning-rate observation")
        windows = [
            ("approach", 80, 169),
            ("stationary", 177, 256),
            ("lighting", 205, 249),
            ("return", 270, 379),
            ("empty", 420, 524),
        ]
        for name, start, end in windows:
            selected = rows[start : end + 1]
            counts = {
                key: sum(row[key] for row in selected)
                for key in rows[0]
                if key != "frame"
            }
            foreground = counts["fg_pixels"]
            row = dict(
                rate=rate,
                window=name,
                start=start,
                end=end,
                foreground_recall=counts["tp"] / foreground if foreground else "",
                background_fpr=counts["fp"] / counts["bg_pixels"],
            )
            for label in ("background", "shadow", "foreground"):
                row[f"person_raw_{label}_fraction"] = (
                    counts[f"person_raw_{label}"] / foreground if foreground else ""
                )
            summary.append(row)
    return summary, images


def main(argv: list[str] | None = None) -> None:
    from experiments.storage import publish_results, result_arguments, result_directory

    args = result_arguments("learning-rate", argv)
    validate_inputs()
    initialize_reproducibility()
    with result_directory(args.output, "learning-rate") as output:
        details = output / "details" if args.details else None
        if details is not None:
            details.mkdir()
        rows, images = run(details)
        publish_results(
            output,
            "learning-rate",
            rows,
            images,
            environment([TRACKER / "inputs/17.mp4"]),
            details=args.details,
        )


if __name__ == "__main__":
    main()

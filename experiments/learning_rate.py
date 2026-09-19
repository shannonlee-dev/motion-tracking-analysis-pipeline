"""Reproduce learning-rate masks and LASIESTA pixel metrics."""

from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

from datasets.paths import TRACKER
from experiments.storage import write_csv
from motion_tracking.config import DEFAULT_CONFIG
from motion_tracking.motion import MotionDetector


def run(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    cv2.setNumThreads(1)
    summary = []
    for rate in (0.001, 0.01, 0.1):
        cap = cv2.VideoCapture(str(TRACKER / "inputs/17.mp4"))
        detector = MotionDetector(replace(DEFAULT_CONFIG, learning_rate=rate))
        # An identical separate model exposes labels before threshold/morphology.
        raw_model = cv2.createBackgroundSubtractorMOG2(
            history=DEFAULT_CONFIG.history,
            varThreshold=DEFAULT_CONFIG.var_threshold,
            detectShadows=True,
        )
        rows = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            index = len(rows)
            _, mask = detector.detect(frame)
            raw = raw_model.apply(frame, learningRate=rate)
            gt = cv2.imread(
                str(TRACKER / f"raw/lasiesta/I_IL_02-GT/I_IL_02-GT_{index + 1}.png")
            )
            if gt is None or gt.shape != frame.shape:
                raise ValueError(f"Missing or mismatched GT at {index}")
            foreground = np.all(gt == (0, 0, 255), axis=2) | np.all(gt == 255, axis=2)
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
        cap.release()
        if len(rows) != 525:
            raise ValueError(f"Expected 525 frames, got {len(rows)}")
        write_csv(output / f"learning_rate_{rate}_gt.csv", rows)
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
    write_csv(output / "learning_rate_summary.csv", summary)
    print("Wrote 1,575 pixel-level measurements and 15 window summaries")


def main() -> None:
    from experiments.measurements import measure_learning_rates

    output = Path("results/tracker/runs/latest") / "learning_rate"
    measure_learning_rates(output)
    run(output)


if __name__ == "__main__":
    main()

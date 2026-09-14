"""LASIESTA pixel evaluation with unchanged app MOG2, three learning rates."""
from dataclasses import replace
import cv2
import numpy as np
from scripts.constants import (
    LEARNING_RATES, BASELINE_LEARNING_RATE, CURRENT_RESULTS_DIR, LASIESTA_EXTRACTED_DIR,
)
from motion_tracking.config import Config, DEFAULT_CONFIG
from motion_tracking.vision import MotionDetector
from scripts.common import write_csv, RESULTS, ROOT
from scripts.data.lasiesta import labels, sequence_paths

def confusion(pred, fg, valid):
    return tuple(int(np.count_nonzero(x & valid)) for x in
                 (pred & fg, pred & ~fg, ~pred & fg, ~pred & ~fg))


SEQUENCES = ('I_IL_01', 'I_IL_02')
RECOVERY_FPR_THRESHOLD = 0.01
RECOVERY_CONSECUTIVE_FRAMES = 10
WARMUP_FRAMES = DEFAULT_CONFIG.warmup_frames


def main():
    results = RESULTS/CURRENT_RESULTS_DIR
    (results/'captures').mkdir(parents=True, exist_ok=True)
    rows, frames = [], []
    for seq in SEQUENCES:
        root = ROOT/LASIESTA_EXTRACTED_DIR
        paths = sequence_paths(root, seq)
        count = len(paths)
        images = [cv2.imread(str(p)) for p, _ in paths]
        gt = [cv2.imread(str(p)) for _, p in paths]
        if any(x is None for x in images+gt):
            raise ValueError('Missing LASIESTA frame or annotation')
        truth = [labels(x) for x in gt]
        luminance = [float(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY).mean()) for x in images]
        jump = int(np.argmax(np.abs(np.diff(luminance))[WARMUP_FRAMES:]))+WARMUP_FRAMES+2  # original 1-based frame
        for rate in LEARNING_RATES:
            detector = MotionDetector(replace(Config(), learning_rate=rate))
            total = np.zeros(4, dtype=np.int64)
            panels, rates = [], []
            selected = {WARMUP_FRAMES+1, max(WARMUP_FRAMES+1, jump-1), jump,
                        min(count, jump+RECOVERY_CONSECUTIVE_FRAMES), count}
            for i, (im, (fg, valid)) in enumerate(zip(images, truth), 1):
                _, mask = detector.detect(im)
                counts = confusion(mask > 0, fg, valid)
                tp, fp, fn, tn = counts
                if i > WARMUP_FRAMES:
                    total += counts
                fpr = fp/(fp+tn) if fp+tn else 0.0
                rates.append(fpr)
                frames.append(dict(sequence=seq, learning_rate=rate, frame=i,
                                   excluded=int(i <= WARMUP_FRAMES), luminance=luminance[i-1],
                                   tp=tp, fp=fp, fn=fn, tn=tn, background_fpr=fpr))
                if i in selected:
                    panel = np.concatenate([im, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), gt[i-1]], axis=1)
                    cv2.putText(panel, f'{seq} f{i} lr={rate}: RGB | prediction | GT',
                                (8, 20), 0, .5, (0, 255, 255), 1)
                    panels.append(panel)
            recovery = next((i+1 for i in range(jump-1, count-RECOVERY_CONSECUTIVE_FRAMES+1)
                             if all(v <= RECOVERY_FPR_THRESHOLD for v in rates[i:i+RECOVERY_CONSECUTIVE_FRAMES])), None)
            tp, fp, fn, tn = map(int, total)
            rows.append(dict(sequence=seq, learning_rate=rate, frames=count,
                             evaluated_frames=count-WARMUP_FRAMES, width=images[0].shape[1],
                             height=images[0].shape[0], tp=tp, fp=fp, fn=fn, tn=tn,
                             precision=tp/(tp+fp) if tp+fp else 0,
                             recall=tp/(tp+fn) if tp+fn else 0,
                             f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,
                             background_fpr=fp/(fp+tn), largest_luminance_jump_frame=jump,
                             recovery_start_frame=recovery,
                             recovery_delay_frames=recovery-jump if recovery else None))
            if seq in SEQUENCES and rate == BASELINE_LEARNING_RATE:
                cv2.imwrite(str(results/f'captures/{seq}_{rate}.jpg'), np.concatenate(panels, axis=0))
    write_csv(results/'lasiesta_summary.csv', rows)
    write_csv(results/'traces/lasiesta_frames.csv', frames)


if __name__ == '__main__':
    main()

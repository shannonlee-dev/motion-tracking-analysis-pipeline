"""LASIESTA pixel evaluation with unchanged app MOG2, three learning rates."""
from dataclasses import replace
import cv2
import numpy as np
from motion_tracking.config import Config
from motion_tracking.vision import MotionDetector
from scripts.common import write_csv, RESULTS, ROOT
from scripts.data.lasiesta import labels, sequence_paths


def confusion(pred, fg, valid):
    return tuple(int(np.count_nonzero(x & valid)) for x in
                 (pred & fg, pred & ~fg, ~pred & fg, ~pred & ~fg))


SEQUENCES = ('I_IL_01', 'I_IL_02')


def main():
    results = RESULTS/'current'
    (results/'captures').mkdir(parents=True, exist_ok=True)
    rows, frames = [], []
    for seq in SEQUENCES:
        root = ROOT/'data/lasiesta/extracted'
        paths = sequence_paths(root, seq)
        count = len(paths)
        images = [cv2.imread(str(p)) for p, _ in paths]
        gt = [cv2.imread(str(p)) for _, p in paths]
        if any(x is None for x in images+gt):
            raise ValueError('Missing LASIESTA frame or annotation')
        truth = [labels(x) for x in gt]
        luminance = [float(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY).mean()) for x in images]
        jump = int(np.argmax(np.abs(np.diff(luminance))[25:]))+27  # original 1-based frame
        for rate in (.001, .01, .1):
            detector = MotionDetector(replace(Config(), learning_rate=rate))
            total = np.zeros(4, dtype=np.int64)
            panels, rates = [], []
            selected = {26, max(26, jump-1), jump, min(count, jump+10), count}
            for i, (im, (fg, valid)) in enumerate(zip(images, truth), 1):
                _, mask = detector.detect(im)
                counts = confusion(mask > 0, fg, valid)
                tp, fp, fn, tn = counts
                if i > 25:
                    total += counts
                fpr = fp/(fp+tn) if fp+tn else 0.0
                rates.append(fpr)
                frames.append(dict(sequence=seq, learning_rate=rate, frame=i,
                                   excluded=int(i <= 25), luminance=luminance[i-1],
                                   tp=tp, fp=fp, fn=fn, tn=tn, background_fpr=fpr))
                if i in selected:
                    panel = np.concatenate([im, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), gt[i-1]], axis=1)
                    cv2.putText(panel, f'{seq} f{i} lr={rate}: RGB | prediction | GT',
                                (8, 20), 0, .5, (0, 255, 255), 1)
                    panels.append(panel)
            recovery = next((i+1 for i in range(jump-1, count-9)
                             if all(v <= .01 for v in rates[i:i+10])), None)
            tp, fp, fn, tn = map(int, total)
            rows.append(dict(sequence=seq, learning_rate=rate, frames=count,
                             evaluated_frames=count-25, width=images[0].shape[1],
                             height=images[0].shape[0], tp=tp, fp=fp, fn=fn, tn=tn,
                             precision=tp/(tp+fp) if tp+fp else 0,
                             recall=tp/(tp+fn) if tp+fn else 0,
                             f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,
                             background_fpr=fp/(fp+tn), largest_luminance_jump_frame=jump,
                             recovery_start_frame=recovery,
                             recovery_delay_frames=recovery-jump if recovery else None))
            if seq in ('I_IL_01', 'I_IL_02') and rate == .01:
                cv2.imwrite(str(results/f'captures/{seq}_{rate}.jpg'), np.concatenate(panels, axis=0))
    write_csv(results/'lasiesta_summary.csv', rows)
    write_csv(results/'traces/lasiesta_frames.csv', frames)


if __name__ == '__main__':
    main()

"""Reproduce submission measurements with the unmodified application classes."""
import csv
import hashlib
import json
import platform
import subprocess
from dataclasses import asdict, replace
from pathlib import Path

import cv2
import numpy as np

from motion_tracking.config import DEFAULT_CONFIG
from motion_tracking.vision import MotionDetector, TargetMatcher
from motion_tracking.tracker import Tracker
from scripts.data.prepare_jogging_matching import SELECTIONS

OUT = Path('results/submission')


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cv2.setNumThreads(1)
    cv2.setRNGSeed(0)
    matcher = TargetMatcher(cv2.imread('data/matching_inputs/target.png'))
    selected = {s[2]-1: s for s in SELECTIONS}
    cap = cv2.VideoCapture('data/matching_inputs/jogging.mp4')
    rows = []
    index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if index in selected:
            slug, label, source, _ = selected[index]
            label = label.replace('° 방향 변화', '도 회전')
            result = matcher.match(frame)
            rows.append(dict(condition=label, video='data/matching_inputs/jogging.mp4',
                             frame=index, source_jpg_frame=source,
                             keypoints=result.keypoints, matches=result.matches,
                             target_keypoints=len(matcher.target_kp),
                             rate=100*result.matches/len(matcher.target_kp),
                             inliers=result.inliers, found=result.found))
            cv2.imwrite(str(OUT / f'feature_{slug}.png'), frame)
        index += 1
    cap.release()
    rows.sort(key=lambda r: list(selected).index(r['frame']))
    write_csv(OUT/'features.csv', rows)
    metadata = dict(python=platform.python_version(), opencv=cv2.__version__,
                    numpy=np.__version__, platform=platform.platform(),
                    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                    config=asdict(DEFAULT_CONFIG), seed=0, threads=1)
    metadata['input_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [*Path('data/tracking_inputs').glob('*'),
                  Path('data/matching_inputs/jogging.mp4'), Path('data/matching_inputs/target.png')]}
    metadata['production_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in Path('motion_tracking').glob('*.py')}
    (OUT/'environment.json').write_text(json.dumps(metadata, indent=2)+'\n')
    for rate in (.001,.01,.1):
        detector = MotionDetector(replace(DEFAULT_CONFIG, learning_rate=rate))
        cap = cv2.VideoCapture('data/tracking_inputs/17.mp4')
        rows=[]; tiles=[]; index=0
        while True:
            ok, frame=cap.read()
            if not ok: break
            boxes, mask=detector.detect(frame)
            rows.append(dict(frame=index, foreground_pixels=int(np.count_nonzero(mask)),
                             foreground_fraction=float(np.mean(mask>0)), boxes=len(boxes),
                             mean_gray=float(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY).mean())))
            if index in (100,170,190,210,240,270,300,350,420):
                im=frame.copy()
                for x,y,w,h in boxes: cv2.rectangle(im,(x,y),(x+w,y+h),(0,255,0),2)
                a=cv2.resize(im,(320,240)); b=cv2.resize(cv2.cvtColor(mask,cv2.COLOR_GRAY2BGR),(320,240))
                cv2.putText(a,f'LR {rate} f{index}',(5,20),0,.6,(0,255,255),1)
                tiles.append(np.hstack([a,b]))
            index+=1
        cap.release()
        write_csv(OUT/f'learning_rate_{rate}.csv',rows)
        cv2.imwrite(str(OUT/f'learning_rate_{rate}.jpg'),np.vstack(tiles))
        print('learning rate',rate,'frames',index,flush=True)
    for path in sorted(Path('data/tracking_inputs').glob('*')):
        if path.stem in ('12', '13'):
            continue
        cap=cv2.VideoCapture(str(path)); detector=MotionDetector()
        variants={'default':Tracker(),'distance_80':Tracker(max_distance=80),
                  'missing_30':Tracker(max_missing=30),'velocity':Tracker(predict_velocity=True)}
        records={key:[] for key in variants}; index=0
        while True:
            ok,frame=cap.read()
            if not ok: break
            boxes,_=detector.detect(frame)
            for key,tracker in variants.items():
                tracks=tracker.update(boxes)
                records[key].append(dict(frame=index,tracks={tid:list(t.bbox) for tid,t in tracks.items() if t.missing==0}))
            index+=1
        cap.release()
        for key,record in records.items():
            (OUT/f'tracks_{path.stem}_{key}.json').write_text(json.dumps(record,separators=(',',':'))+'\n')
        print(path,index,flush=True)


if __name__=='__main__': main()

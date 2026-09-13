"""Deterministic scenes and feature/background experiments, generated on demand."""
from pathlib import Path
import tempfile
import cv2
import numpy as np
from app import run
from motion_tracking.config import Config
from scripts.common import ROOT, RESULTS
from motion_tracking.vision import MotionDetector, TargetMatcher

FPS, FRAMES = 25, 625
CONDITIONS = {'single': 10, 'crossing': 10, 'stopping': 5, 'lighting': 5}

def synthetic_frame(condition, trial, frame_number):
    """25 s, known rectangles: enter f50, exit f575, cross f300.

    Rear object is rendered first, so its occlusion fraction is exact.
    Trial changes y offset, speed and object width deterministically.
    """
    image = np.full((240, 320, 3), (55, 65, 75), np.uint8)
    cv2.line(image, (0, 190), (319, 190), (70, 80, 90), 2)
    truth, excluded = {}, {}
    if 50 <= frame_number < 575:
        t = (frame_number-50)/500
        width, height = 30+trial%3*2, 48
        y = 105+(trial%5-2)*5
        if condition == 'stopping':
            if frame_number < 230:
                x = 30+(frame_number-50)*.4
            elif frame_number <= 380:
                x = 102
            else:
                x = 102+(frame_number-380)*.55
        else:
            x = 30+(240-width)*t
        truth[1] = (int(x), y, width, height)
        excluded[1] = False
        if condition == 'crossing':
            truth[2] = (int(240-(240-width)*t), y+trial%2*4, width, height)
            excluded[2] = False
            ax, ay, aw, ah = truth[1]
            bx, by, bw, bh = truth[2]
            overlap = max(0,min(ax+aw,bx+bw)-max(ax,bx))*max(0,min(ay+ah,by+bh)-max(ay,by))
            excluded[1] = overlap/(aw*ah) >= .5
        for tid, (x, y, w, h) in truth.items():
            color = (160,190,230) if tid == 1 else (220,150,95)
            cv2.rectangle(image,(x,y),(x+w-1,y+h-1),color,-1)
            cv2.line(image,(x+4,y+5),(x+w-5,y+h-6),(45,45,45),2)
            cv2.putText(image,str(tid),(x+5,y+30),0,.6,(20,20,20),1)
    if condition == 'lighting' and frame_number >= 300:
        image = cv2.add(image, np.full_like(image, 70+trial*5))
    return image, truth, excluded


def make_target():
    rng=np.random.default_rng(42)
    target=np.full((180,180,3),235,np.uint8)
    for _ in range(180):
        center=tuple(map(int,rng.integers(8,172,2)))
        color=tuple(map(int,rng.integers(20,220,3)))
        cv2.circle(target,center,int(rng.integers(2,7)),color,-1)
    cv2.rectangle(target,(3,3),(176,176),(20,20,20),3)
    cv2.putText(target,'CV TARGET',(13,94),0,.7,(0,0,0),2)
    return target


def make_target_demo(path, target):
    """Write a reproducible test input to an explicitly chosen location."""
    canvas = np.full((320, 320, 3), 55, np.uint8)
    canvas[70:250, 70:250] = target
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), FPS, (320, 320))
    if not writer.isOpened():
        raise OSError('Cannot create target demo')
    try:
        for f in range(FRAMES):
            if f < 50 or f >= 575:
                frame = np.full_like(canvas, 55)
            else:
                matrix = cv2.getRotationMatrix2D((160, 160), (f-50)*.12, 1)
                matrix[0, 2] = 20*np.sin(f/50)
                frame = cv2.warpAffine(canvas, matrix, (320, 320), borderValue=(55, 55, 55))
            writer.write(frame)
    finally:
        writer.release()


def feature_experiment(export_videos=False):
    target=make_target()
    matcher=TargetMatcher(target)
    rows,panels=[],[]
    conditions=[('front',0,0),('rotate30',30,0),('rotate60',60,0),('occlusion30',0,.3),('occlusion50',0,.5)]
    canvas=np.full((320,320,3),55,np.uint8)
    canvas[70:250,70:250]=target
    for label,angle,occlusion in conditions:
        for trial in range(10):
            matrix=cv2.getRotationMatrix2D((160,160),angle,1)
            matrix[:,2]+=np.array([trial%5-2,trial//5-1])
            frame=cv2.warpAffine(canvas,matrix,(320,320),borderValue=(55,55,55))
            if occlusion:
                x=70+trial%5-2; y=70+trial//5-1
                frame[y:y+180,x:x+round(180*occlusion)]=55
            result=matcher.match(frame)
            rows.append(dict(condition=label,trial=trial+1,reference_keypoints=len(matcher.target_kp),
                             scene_keypoints=result.keypoints,matches=result.matches,inliers=result.inliers,
                             match_rate=round(result.matches/len(matcher.target_kp),6),found=int(result.found)))
            if trial==0:
                image=frame.copy()
                if result.found:
                    cv2.polylines(image,[result.polygon],True,(0,255,255),2)
                cv2.putText(image,f'{label} {result.matches} matches',(5,25),0,.5,(255,255,255),1)
                panels.append(image)
    cv2.imwrite(str(RESULTS/'captures/features.jpg'),np.concatenate(panels,axis=1))
    # Test file input with a disposable video; keep it only when explicitly requested.
    with tempfile.TemporaryDirectory(prefix='motion-target-') as temporary:
        destination = ROOT/'data/clips' if export_videos else Path(temporary)
        destination.mkdir(parents=True, exist_ok=True)
        path, target_path = destination/'target_demo.mp4', destination/'target.png'
        cv2.imwrite(str(target_path), target)
        make_target_demo(path, target)
        stats = run(str(path), target=target_path, headless=True,
                    output=RESULTS/'videos/target_demo.mp4' if export_videos else Path(temporary)/'output.mp4',
                    csv_path=RESULTS/'traces/target_demo.csv')
    return rows,stats


def background_experiment():
    rows=[]
    for rate in (.001,.01,.1):
        for kernel in (1,3,7):
            for condition in ('stopping','lighting'):
                detector=MotionDetector(Config(learning_rate=rate,kernel_size=kernel))
                fractions=[]
                for f in range(FRAMES):
                    frame,truth,_=synthetic_frame(condition,0,f)
                    _,mask=detector.detect(frame)
                    if 300<=f<400:
                        fractions.append(float(np.count_nonzero(mask)/mask.size))
                    if kernel == 3 and condition == 'lighting' and rate in (.001, .1) and f == 310:
                        pair=np.concatenate([frame,cv2.cvtColor(mask,cv2.COLOR_GRAY2BGR)],axis=1)
                        cv2.imwrite(str(RESULTS/f'captures/mask_{condition}_{rate}_{f}.jpg'),pair)
                rows.append(dict(condition=condition,learning_rate=rate,kernel=kernel,
                                 mean_foreground_fraction_f300_399=float(np.mean(fractions))))
    return rows

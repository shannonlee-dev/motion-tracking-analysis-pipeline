"""Feature and background experiments on deterministic synthetic inputs."""
from pathlib import Path
import tempfile
import cv2
import numpy as np
from motion_tracking.runner import run
from motion_tracking.config import Config
from scripts.common import ROOT, RESULTS
from scripts.data.synthetic import FRAMES, synthetic_frame, make_target, make_target_demo

from motion_tracking.vision import MotionDetector, TargetMatcher

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

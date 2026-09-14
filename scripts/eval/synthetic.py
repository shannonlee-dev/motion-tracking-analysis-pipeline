"""Feature and background experiments on deterministic synthetic inputs."""
from pathlib import Path
import tempfile
import cv2
import numpy as np
from scripts.constants import (
    LEARNING_RATES, BASELINE_LEARNING_RATE, KERNEL_SIZES, FEATURE_TRIALS, CLIPS_DIR,
)
from motion_tracking.runner import run
from motion_tracking.config import Config
from scripts.common import ROOT, RESULTS
from scripts.data.synthetic import (
    FRAMES, synthetic_frame, make_target, make_target_demo, TARGET_SIZE,
    TARGET_CANVAS_SIZE, TARGET_BACKGROUND, TARGET_OFFSET, TARGET_END, TARGET_CENTER,
    LIGHTING_CHANGE_FRAME,
)
from motion_tracking.vision import MotionDetector, TargetMatcher

FEATURE_CONDITIONS = (
    ('front', 0, 0), ('rotate30', 30, 0), ('rotate60', 60, 0),
    ('occlusion30', 0, .3), ('occlusion50', 0, .5),
)
BACKGROUND_WINDOW_FRAMES = 100
BACKGROUND_CAPTURE_FRAME = LIGHTING_CHANGE_FRAME+10


def feature_experiment(
    export_videos: bool = False,
) -> tuple[list[dict[str, object]], dict[str, int | float]]:
    target=make_target()
    matcher=TargetMatcher(target)
    rows,panels=[],[]
    canvas=np.full((TARGET_CANVAS_SIZE,TARGET_CANVAS_SIZE,3),TARGET_BACKGROUND,np.uint8)
    canvas[TARGET_OFFSET:TARGET_END,TARGET_OFFSET:TARGET_END]=target
    for label,angle,occlusion in FEATURE_CONDITIONS:
        for trial in range(FEATURE_TRIALS):
            matrix=cv2.getRotationMatrix2D(TARGET_CENTER,angle,1)
            matrix[:,2]+=np.array([trial%5-2,trial//5-1])
            frame=cv2.warpAffine(canvas,matrix,(TARGET_CANVAS_SIZE,TARGET_CANVAS_SIZE),borderValue=(TARGET_BACKGROUND,)*3)
            if occlusion:
                x=TARGET_OFFSET+trial%5-2; y=TARGET_OFFSET+trial//5-1
                frame[y:y+TARGET_SIZE,x:x+round(TARGET_SIZE*occlusion)]=TARGET_BACKGROUND
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
        destination = ROOT/CLIPS_DIR if export_videos else Path(temporary)
        destination.mkdir(parents=True, exist_ok=True)
        path, target_path = destination/'target_demo.mp4', destination/'target.png'
        cv2.imwrite(str(target_path), target)
        make_target_demo(path, target)
        stats = run(str(path), target=target_path, headless=True,
                    output=RESULTS/'videos/target_demo.mp4' if export_videos else Path(temporary)/'output.mp4',
                    csv_path=RESULTS/'traces/target_demo.csv')
    return rows,stats


def background_experiment() -> list[dict[str, object]]:
    rows=[]
    for rate in LEARNING_RATES:
        for kernel in KERNEL_SIZES:
            for condition in ('stopping','lighting'):
                detector=MotionDetector(Config(learning_rate=rate,kernel_size=kernel))
                fractions=[]
                for f in range(FRAMES):
                    frame,truth,_=synthetic_frame(condition,0,f)
                    _,mask=detector.detect(frame)
                    if LIGHTING_CHANGE_FRAME<=f<LIGHTING_CHANGE_FRAME+BACKGROUND_WINDOW_FRAMES:
                        fractions.append(float(np.count_nonzero(mask)/mask.size))
                    if kernel == 3 and condition == 'lighting' and rate != BASELINE_LEARNING_RATE and f == BACKGROUND_CAPTURE_FRAME:
                        pair=np.concatenate([frame,cv2.cvtColor(mask,cv2.COLOR_GRAY2BGR)],axis=1)
                        cv2.imwrite(str(RESULTS/f'captures/mask_{condition}_{rate}_{f}.jpg'),pair)
                rows.append(dict(condition=condition,learning_rate=rate,kernel=kernel,
                                 mean_foreground_fraction_f300_399=float(np.mean(fractions))))
    return rows

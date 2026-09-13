"""Run the 30 controlled trials and parameter comparisons. Video export is opt-in."""
import argparse
from dataclasses import asdict, replace
import json
import platform
import time
import cv2
import numpy as np
from motion_tracking.config import Config
from scripts.common import RESULTS, write_csv
from scripts.eval.tracking import evaluate_synthetic, evaluate_real
from scripts.eval.synthetic import CONDITIONS, feature_experiment, background_experiment

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-videos', action='store_true', help='also save synthetic inputs and annotated videos')
    args = parser.parse_args()
    cv2.setNumThreads(1)
    cv2.setRNGSeed(42)
    for directory in ('captures','traces'):
        (RESULTS/directory).mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    config=Config()
    variants={
        'baseline':config,
        'lr_0.001':replace(config,learning_rate=.001),
        'lr_0.1':replace(config,learning_rate=.1),
        'kernel_1':replace(config,kernel_size=1),
        'kernel_7':replace(config,kernel_size=7),
        'distance_20':replace(config,max_distance=20),
        'distance_80':replace(config,max_distance=80),
        'velocity':replace(config,predict_velocity=True),
    }
    allrows=[]
    for label,cfg in variants.items():
        print('Running',label,flush=True)
        allrows.extend(evaluate_synthetic(cfg,label,export=label=='baseline',export_videos=args.export_videos))
    write_csv(RESULTS/'tracking_trials.csv',allrows)
    print('Running CAVIAR and ORB',flush=True)
    write_csv(RESULTS/'current/real_tracking.csv',evaluate_real(config, export_videos=args.export_videos))
    features,target_stats=feature_experiment(export_videos=args.export_videos)
    write_csv(RESULTS/'features.csv',features)
    write_csv(RESULTS/'background.csv',background_experiment())
    summary=[]
    for variant in variants:
        for condition in CONDITIONS:
            group=[r for r in allrows if r['variant']==variant and r['condition']==condition]
            eligible=sum(r['eligible_frames'] for r in group)
            summary.append(dict(variant=variant,condition=condition,trials=len(group),
                                id_switches=sum(r['id_switches'] for r in group),
                                post_overlap_switches=sum(r['post_overlap_switches'] for r in group)
                                    if condition == 'crossing' else '',
                                failures=sum(r['failures'] for r in group),
                                failed_trials=sum(r['failure_event'] for r in group),
                                failure_rate=sum(r['failure_event'] for r in group)/len(group),
                                switch_trials=sum(r['switch_event'] for r in group),
                                miss_rate=sum(r['missing_frames'] for r in group)/max(eligible,1)))
    write_csv(RESULTS/'tracking_summary.csv',summary)
    (RESULTS/'run.json').write_text(json.dumps(dict(python=platform.python_version(),opencv=cv2.__version__,
        numpy=np.__version__,config=asdict(config),seed=42,threads=1,
        elapsed_seconds=time.perf_counter()-started,target_demo=target_stats),indent=2)+'\n')
    print(json.dumps(summary[:4],indent=2),flush=True)


if __name__ == "__main__":
    main()

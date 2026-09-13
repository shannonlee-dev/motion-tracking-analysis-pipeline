"""CAVIAR and controlled tracking evaluation; no dataset downloads or report imports."""
import xml.etree.ElementTree as ET
import cv2
import numpy as np
from motion_tracking.display import draw_overlay
from motion_tracking.evaluation import assign_ground_truth, count_events, count_post_overlap_switches, iou
from scripts.common import ROOT, RESULTS, write_csv
from scripts.eval.synthetic import FPS, FRAMES, CONDITIONS, synthetic_frame
from motion_tracking.tracker import Tracker
from motion_tracking.vision import MotionDetector

def load_caviar(path):
    result = {}
    for frame in ET.parse(path).getroot().findall('frame'):
        objects = {}
        for obj in frame.findall('./objectlist/object'):
            box = obj.find('box')
            if box is None:
                continue
            xc,yc,w,h = [float(box.get(k)) for k in ('xc','yc','w','h')]
            objects[int(obj.get('id'))] = (xc-w/2,yc-h/2,w,h)
        result[int(frame.get('number'))] = objects
    return result


def match_eligible(truth, tracks, excluded):
    eligible = {tid: box for tid, box in truth.items() if not excluded.get(tid, False)}
    matched = assign_ground_truth(eligible, tracks)
    return {tid: matched.get(tid) for tid in truth}


def summarize(video, condition, assignments, exclusion, first_last, note):
    totals = dict(id_switches=0, failures=0, missing_frames=0, eligible_frames=0, excluded_frames=0)
    objects = []
    for tid, values in assignments.items():
        metrics = count_events(values, exclusion[tid])
        objects.append(dict(video=video, condition=condition, gt_id=tid,
                            frame_start=first_last[tid][0], frame_end=first_last[tid][1], **metrics))
        for key in totals:
            totals[key] += metrics[key]
    row = dict(video=video, condition=condition, frame_start=min(v[0] for v in first_last.values()),
               frame_end=max(v[1] for v in first_last.values()), **totals,
               failure_event=int(totals['failures']>0), switch_event=int(totals['id_switches']>0),
               miss_rate=round(totals['missing_frames']/max(totals['eligible_frames'],1),6), note=note)
    return row, objects


def evaluate_synthetic(config, variant, export=False, export_videos=False):
    rows, object_rows = [], []
    for condition, count in CONDITIONS.items():
        for trial in range(count):
            detector = MotionDetector(config)
            tracker = Tracker(config.max_distance,config.max_missing,config.trail_length,config.predict_velocity)
            assignments, exclusions, first_last, traces = {}, {}, {}, []
            overlap_frames = []
            video = f'{condition}_{trial+1:02d}'
            writer = overlay_writer = None
            panels = []
            if export and export_videos:
                (ROOT/'data/clips').mkdir(parents=True, exist_ok=True)
                (RESULTS/'videos').mkdir(parents=True, exist_ok=True)
                writer = cv2.VideoWriter(str(ROOT/f'data/clips/{video}.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),FPS,(320,240))
                if not writer.isOpened():
                    raise OSError('Cannot open synthetic video writer')
                overlay_writer = cv2.VideoWriter(str(RESULTS/f'videos/{video}.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),FPS,(320,240))
                if not overlay_writer.isOpened():
                    writer.release()
                    raise OSError('Cannot open overlay writer')
            for f in range(FRAMES):
                frame, truth, excluded = synthetic_frame(condition,trial,f)
                # Physical overlap starts before the >=50% rear-object exclusion.
                if condition == 'crossing' and len(truth) == 2 and iou(truth[1], truth[2]) > 0:
                    overlap_frames.append(f)
                boxes, mask = detector.detect(frame)
                tracks = tracker.update(boxes)
                matches = match_eligible(truth,tracks,excluded)
                for tid in truth:
                    assignments.setdefault(tid,[]).append(matches[tid])
                    exclusions.setdefault(tid,[]).append(excluded[tid])
                    first_last.setdefault(tid,[f,f])[1] = f
                    if export:
                        traces.append(dict(frame=f,gt_id=tid,track_id=matches[tid],excluded=int(excluded[tid]),
                                           x=truth[tid][0],y=truth[tid][1],w=truth[tid][2],h=truth[tid][3]))
                if export:
                    if writer:
                        writer.write(frame)
                    overlay = draw_overlay(frame,tracks,0,f)
                    if overlay_writer:
                        overlay_writer.write(overlay)
                    if f in (100,250,290,300,320,380,450):
                        panels.append(overlay)
            if writer:
                writer.release()
            if overlay_writer:
                overlay_writer.release()
            row, objrows = summarize(video,condition,assignments,exclusions,first_last,
                                      'synthetic; one scripted event; exact rear-object occlusion mask')
            row = dict(variant=variant,**row)
            row.update(overlap_start=overlap_frames[0] if overlap_frames else '',
                       overlap_end=overlap_frames[-1] if overlap_frames else '',
                       post_overlap_switches=0 if overlap_frames else '')
            for obj in objrows:
                tid = obj['gt_id']
                obj.update(overlap_start=row['overlap_start'], overlap_end=row['overlap_end'],
                           post_overlap_switches='')
                if overlap_frames:
                    offset = first_last[tid][0]
                    obj['post_overlap_switches'] = count_post_overlap_switches(
                        assignments[tid], exclusions[tid],
                        overlap_frames[0]-offset, overlap_frames[-1]-offset)
                    row['post_overlap_switches'] += obj['post_overlap_switches']
            rows.append(row)
            object_rows.extend(objrows)
            if export:
                write_csv(RESULTS/f'traces/{video}.csv',traces)
                if trial == 0 and condition in ('crossing', 'stopping'):
                    cv2.imwrite(str(RESULTS/f'captures/{video}.jpg'),np.concatenate(panels,axis=1))
    if export:
        write_csv(RESULTS/'synthetic_objects.csv',object_rows)
    return rows


def evaluate_real(config, export_videos=False):
    results = RESULTS/'current'
    (results/'captures').mkdir(parents=True, exist_ok=True)
    rows, allobjects, metadata = [], [], []
    for name in ('walking', 'meeting', 'stopping'):
        truth_frames = load_caviar(ROOT/f'data/raw/{name}.xml')
        cap = cv2.VideoCapture(str(ROOT/f'data/raw/{name}.mpg'))
        detector = MotionDetector(config)
        tracker = Tracker(config.max_distance,config.max_missing,config.trail_length)
        assignments, exclusions, first_last, traces, panels = {}, {}, {}, [], []
        writer = None
        if export_videos:
            (results/'videos').mkdir(parents=True, exist_ok=True)
            writer = cv2.VideoWriter(str(results/f'videos/caviar_{name}.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),FPS,(384,288))
        if not cap.isOpened() or (writer is not None and not writer.isOpened()):
            raise OSError('Cannot open CAVIAR video/writer')
        f=0
        while True:
            ok,frame=cap.read()
            if not ok:
                break
            boxes,mask=detector.detect(frame)
            tracks=tracker.update(boxes)
            truth=truth_frames.get(f,{})
            matches=assign_ground_truth(truth,tracks)
            # Missing XML frame is excluded, not interpolated or fabricated.
            for tid in set(assignments)|set(truth):
                present = tid in truth
                skip = not present or f < config.warmup_frames
                assignments.setdefault(tid,[]).append(matches.get(tid))
                exclusions.setdefault(tid,[]).append(skip)
                if present:
                    first_last.setdefault(tid,[f,f])[1]=f
                    traces.append(dict(frame=f,gt_id=tid,track_id=matches.get(tid),excluded=int(skip),
                                       x=truth[tid][0],y=truth[tid][1],w=truth[tid][2],h=truth[tid][3]))
            overlay=draw_overlay(frame,tracks,0,f)
            if writer is not None:
                writer.write(overlay)
            if f in (50,100,150,175,200,250,300,400,500,600):
                for tid,(x,y,w,h) in truth.items():
                    cv2.rectangle(overlay,(int(x),int(y)),(int(x+w),int(y+h)),(255,255,255),1)
                    cv2.putText(overlay,f'GT{tid}',(int(x),int(y+h)+10),0,.35,(255,255,255),1)
                panels.append(overlay)
            f+=1
        cap.release()
        if writer is not None:
            writer.release()
        if not f:
            raise ValueError('Empty CAVIAR clip')
        row,objects=summarize(name,'real',assignments,exclusions,first_last,
                              'CAVIAR MPEG frame-index join; occlusion not annotated: raw counts, not mission-adjusted')
        rows.append(row); allobjects.extend(objects)
        metadata.append(dict(video=name,decoded_frames=f,xml_frames=len(truth_frames),seconds=f/FPS))
        write_csv(results/f'traces/caviar_{name}.csv',traces)
        if name == 'meeting':
            cv2.imwrite(str(results/f'captures/caviar_{name}.jpg'),np.concatenate(panels,axis=1))
    write_csv(results/'real_objects.csv',allobjects)
    write_csv(results/'video_metadata.csv',metadata)
    return rows

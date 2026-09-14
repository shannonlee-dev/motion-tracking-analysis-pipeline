"""Deterministic scenes, ground truth and target video generation."""
from motion_tracking.constants import VIDEO_CODEC
from pathlib import Path
import cv2
import numpy as np
from motion_tracking.geometry import BBox, intersection_area
from motion_tracking.evaluation import OCCLUSION_EXCLUSION_FRACTION
from scripts.constants import EXPERIMENT_SEED

FPS, FRAMES = 25, 625
FRAME_SIZE = (320, 240)  # OpenCV sizes are (width, height).
OBJECT_ENTER_FRAME = 50
OBJECT_EXIT_FRAME = 575
MOTION_DURATION_FRAMES = 500
STOP_START_FRAME = 230
STOP_END_FRAME = 380
LIGHTING_CHANGE_FRAME = 300
OBJECT_START_X = 30
OBJECT_TRAVEL_BOUND = 240
OBJECT_BASE_WIDTH = 30
OBJECT_HEIGHT = 48
OBJECT_BASE_Y = 105
STOP_X = 102
PRE_STOP_SPEED = 0.4
POST_STOP_SPEED = 0.55
LIGHTING_BASE_INCREASE = 70
LIGHTING_TRIAL_INCREMENT = 5
TARGET_ROTATION_PER_FRAME = 0.12
TARGET_SWAY_AMPLITUDE = 20
TARGET_SWAY_PERIOD_FRAMES = 50
BACKGROUND_COLOR = (55, 65, 75)
OBJECT_COLORS = ((160, 190, 230), (220, 150, 95))
TARGET_SIZE = 180
TARGET_MARK_COUNT = 180
TARGET_CANVAS_SIZE = 320
TARGET_BACKGROUND = 55
TARGET_OFFSET = (TARGET_CANVAS_SIZE-TARGET_SIZE)//2
TARGET_END = TARGET_OFFSET+TARGET_SIZE
TARGET_CENTER = (TARGET_CANVAS_SIZE//2, TARGET_CANVAS_SIZE//2)
CONDITIONS = {'single': 10, 'crossing': 10, 'stopping': 5, 'lighting': 5}

def synthetic_frame(
    condition: str, trial: int, frame_number: int,
) -> tuple[np.ndarray, dict[int, BBox], dict[int, bool]]:
    """25 s, known rectangles: enter f50, exit f575, cross f300.

    Rear object is rendered first, so its occlusion fraction is exact.
    Trial changes y offset, speed and object width deterministically.
    """
    image = np.full((FRAME_SIZE[1], FRAME_SIZE[0], 3), BACKGROUND_COLOR, np.uint8)
    cv2.line(image, (0, 190), (319, 190), (70, 80, 90), 2)
    truth, excluded = {}, {}
    if OBJECT_ENTER_FRAME <= frame_number < OBJECT_EXIT_FRAME:
        t = (frame_number-OBJECT_ENTER_FRAME)/MOTION_DURATION_FRAMES
        width, height = OBJECT_BASE_WIDTH+trial%3*2, OBJECT_HEIGHT
        y = OBJECT_BASE_Y+(trial%5-2)*5
        if condition == 'stopping':
            if frame_number < STOP_START_FRAME:
                x = OBJECT_START_X+(frame_number-OBJECT_ENTER_FRAME)*PRE_STOP_SPEED
            elif frame_number <= STOP_END_FRAME:
                x = STOP_X
            else:
                x = STOP_X+(frame_number-STOP_END_FRAME)*POST_STOP_SPEED
        else:
            x = OBJECT_START_X+(OBJECT_TRAVEL_BOUND-width)*t
        truth[1] = (int(x), y, width, height)
        excluded[1] = False
        if condition == 'crossing':
            truth[2] = (int(OBJECT_TRAVEL_BOUND-(OBJECT_TRAVEL_BOUND-width)*t), y+trial%2*4, width, height)
            excluded[2] = False
            overlap = intersection_area(truth[1], truth[2])
            excluded[1] = overlap/(width*height) >= OCCLUSION_EXCLUSION_FRACTION
        for tid, (x, y, w, h) in truth.items():
            color = OBJECT_COLORS[tid-1]
            cv2.rectangle(image,(x,y),(x+w-1,y+h-1),color,-1)
            cv2.line(image,(x+4,y+5),(x+w-5,y+h-6),(45,45,45),2)
            cv2.putText(image,str(tid),(x+5,y+30),0,.6,(20,20,20),1)
    if condition == 'lighting' and frame_number >= LIGHTING_CHANGE_FRAME:
        image = cv2.add(image, np.full_like(image, LIGHTING_BASE_INCREASE+trial*LIGHTING_TRIAL_INCREMENT))
    return image, truth, excluded


def make_target() -> np.ndarray:
    rng=np.random.default_rng(EXPERIMENT_SEED)
    target=np.full((TARGET_SIZE,TARGET_SIZE,3),235,np.uint8)
    for _ in range(TARGET_MARK_COUNT):
        center=tuple(map(int,rng.integers(8,TARGET_SIZE-8,2)))
        color=tuple(map(int,rng.integers(20,220,3)))
        cv2.circle(target,center,int(rng.integers(2,7)),color,-1)
    cv2.rectangle(target,(3,3),(TARGET_SIZE-4,TARGET_SIZE-4),(20,20,20),3)
    cv2.putText(target,'CV TARGET',(13,94),0,.7,(0,0,0),2)
    return target


def make_target_demo(path: Path, target: np.ndarray) -> None:
    """Write a reproducible test input to an explicitly chosen location."""
    canvas = np.full((TARGET_CANVAS_SIZE, TARGET_CANVAS_SIZE, 3), TARGET_BACKGROUND, np.uint8)
    canvas[TARGET_OFFSET:TARGET_END, TARGET_OFFSET:TARGET_END] = target
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*VIDEO_CODEC), FPS, (TARGET_CANVAS_SIZE, TARGET_CANVAS_SIZE))
    if not writer.isOpened():
        raise OSError('Cannot create target demo')
    try:
        for f in range(FRAMES):
            if f < OBJECT_ENTER_FRAME or f >= OBJECT_EXIT_FRAME:
                frame = np.full_like(canvas, TARGET_BACKGROUND)
            else:
                matrix = cv2.getRotationMatrix2D(TARGET_CENTER, (f-OBJECT_ENTER_FRAME)*TARGET_ROTATION_PER_FRAME, 1)
                matrix[0, 2] = TARGET_SWAY_AMPLITUDE*np.sin(f/TARGET_SWAY_PERIOD_FRAMES)
                frame = cv2.warpAffine(canvas, matrix, (TARGET_CANVAS_SIZE, TARGET_CANVAS_SIZE), borderValue=(TARGET_BACKGROUND,)*3)
            writer.write(frame)
    finally:
        writer.release()

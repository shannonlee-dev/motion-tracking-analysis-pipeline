"""Reproduce the visually selected Jogging-1 ORB/SIFT experiment.

Run: python -m scripts.data.prepare_jogging_matching [--video]
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import cv2
import numpy as np

from motion_tracking.features import unique_ratio_matches

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ROOT / "data/matching_inputs/Jogging-1"
ASSETS = ROOT / "data/matching_assets/Jogging-1"
RAW_ASSETS = ASSETS / "raw"
SOURCE = RAW_ASSETS / "Jogging"
SELECTED_FRAMES = ASSETS / "selected_frames"
OUTPUT = ROOT / "results/jogging_matching"
TARGET_FRAME = 1
SCALE = 4
RATIO = 0.75
# Fixed after inspecting all 307 frames, before measuring matches.
SELECTIONS = [
    ("front", "정면", 33, "얼굴과 상체 앞면이 보이는 비가림 프레임; target과 다른 시점"),
    ("rotation_30", "약 30° 방향 변화", 140, "얼굴·어깨가 초기 정면보다 오른쪽으로 향하는 약한 사선 자세"),
    ("rotation_60", "약 60° 방향 변화", 300, "얼굴 측면과 오른쪽을 향한 어깨가 보이는 더 큰 사선 자세"),
    ("occlusion_30", "약 30% 가림", 65, "전봇대 부착물이 몸의 오른쪽 일부를 가림; 얼굴과 왼쪽 몸은 보임"),
    ("occlusion_50", "약 50% 가림", 68, "전봇대와 부착물이 몸통·다리의 상당 부분을 가림"),
]


def write_image(path, image):
    if not cv2.imwrite(str(path), image):
        raise OSError(f"Could not write {path}")


def crop(image, bbox):
    """Convert OTB/MATLAB 1-based x,y to a 0-based half-open crop."""
    x, y, width, height = map(int, bbox)
    x, y = x - 1, y - 1
    if not (0 <= x < x + width <= image.shape[1]
            and 0 <= y < y + height <= image.shape[0]):
        raise ValueError(f"Out-of-image GT: {bbox}")
    return image[y:y + height, x:x + width].copy()


def matching_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", action="store_true", help="Create a 25 fps viewing MP4")
    args = parser.parse_args()
    cv2.setNumThreads(1)
    cv2.setRNGSeed(0)
    archive = ROOT / "data/raw/OTB/Jogging.zip"
    INPUTS.mkdir(parents=True, exist_ok=True)
    RAW_ASSETS.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        for name in zipped.namelist():
            if not (RAW_ASSETS / name).resolve().is_relative_to(RAW_ASSETS.resolve()):
                raise ValueError(f"Unsafe ZIP member: {name}")
        zipped.extractall(RAW_ASSETS)

    paths = sorted((SOURCE / "img").glob("*.jpg"))
    gt_path = SOURCE / "groundtruth_rect.1.txt"
    gt = np.loadtxt(gt_path, dtype=int)
    if [p.name for p in paths] != [f"{n:04d}.jpg" for n in range(1, 308)] or gt.shape != (307, 4):
        raise ValueError("Expected exactly 307 numbered frames and 307 Jogging-1 GT rows")
    images = [cv2.imread(str(p)) for p in paths]
    for frame, (image, bbox) in enumerate(zip(images, gt), 1):
        if image is None or image.shape != (288, 352, 3):
            raise ValueError(f"Invalid frame {frame}")
        crop(image, bbox)
    for directory in (INPUTS, ASSETS, SELECTED_FRAMES, OUTPUT, OUTPUT / "matches",
                      OUTPUT / "keypoints", OUTPUT / "inspection"):
        directory.mkdir(parents=True, exist_ok=True)

    # Full-sequence visual evidence, with the Jogging-1 GT highlighted.
    thumbnails = []
    for number, (image, bbox) in enumerate(zip(images, gt), 1):
        image = image.copy()
        x, y, w, h = map(int, bbox)
        cv2.rectangle(image, (x - 1, y - 1), (x + w - 2, y + h - 2), (0, 255, 0), 1)
        cv2.putText(image, f"{number:04d}", (5, 20), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 255), 1)
        thumbnails.append(image)
    for start in range(0, 307, 40):
        tiles = thumbnails[start:start + 40]
        while len(tiles) % 5:
            tiles.append(np.zeros_like(images[0]))
        sheet = np.vstack([np.hstack(tiles[i:i + 5]) for i in range(0, len(tiles), 5)])
        write_image(OUTPUT / "inspection" / f"frames_{start + 1:04d}_{min(start + 40, 307):04d}.jpg", sheet)

    target = crop(images[TARGET_FRAME - 1], gt[TARGET_FRAME - 1])
    write_image(INPUTS / "target.png", target)
    shutil.copyfile(paths[TARGET_FRAME - 1], SELECTED_FRAMES / "target_0001.jpg")
    selection_records = []
    crops = []
    for slug, label, number, reason in SELECTIONS:
        filename = f"{slug}_{number:04d}"
        roi = crop(images[number - 1], gt[number - 1])
        write_image(INPUTS / f"{filename}.png", roi)
        shutil.copyfile(paths[number - 1], SELECTED_FRAMES / f"{filename}.jpg")
        crops.append(roi)
        selection_records.append(dict(condition=label, slug=slug, frame=number,
                                      bbox_xywh_1based=gt[number - 1].tolist(),
                                      reason=reason, approximate=slug != "front"))
    preview = []
    labels = [("target", TARGET_FRAME)] + [(s[0], s[2]) for s in SELECTIONS]
    for (label, number), roi in zip(labels, [target] + crops):
        enlarged = cv2.resize(roi, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
        tile = np.zeros((570, 180, 3), np.uint8)
        tile[35:35 + enlarged.shape[0], :enlarged.shape[1]] = enlarged
        cv2.putText(tile, f"{label} {number}", (3, 22), cv2.FONT_HERSHEY_SIMPLEX,
                    .42, (255, 255, 255), 1)
        preview.append(tile)
    write_image(OUTPUT / "selected_preview.png", np.hstack(preview))
    metadata = dict(
        sequence="Jogging-1", frame_count=307, frame_numbering="1-based JPG filenames",
        zip_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        gt_file="Jogging/groundtruth_rect.1.txt",
        gt_sha256=hashlib.sha256(gt_path.read_bytes()).hexdigest(),
        target_frame=TARGET_FRAME, target_bbox_xywh_1based=gt[TARGET_FRAME - 1].tolist(),
        target_reason="초기 정면에서 얼굴·상체·다리가 보이고 다른 물체의 가림이 없음",
        selections=selection_records,
        approximation_note="각도는 얼굴·상체 방향의 정성적 구간 표기, 가림은 몸 실루엣의 시각적 추정. 정확한 각도/가림률 GT가 아니며 오차 범위도 측정하지 않음.",
    )
    (ASSETS / "selection.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")

    rows, settings = [], {}
    for algorithm, detector, norm in (
        ("ORB", cv2.ORB_create(nfeatures=1500), cv2.NORM_HAMMING),
        ("SIFT", cv2.SIFT_create(nfeatures=1500), cv2.NORM_L2),
    ):
        reference = matching_image(target)
        ref_kp, ref_desc = detector.detectAndCompute(reference, None)
        if ref_desc is None:
            raise ValueError(f"No {algorithm} descriptors in target")
        matcher = cv2.BFMatcher(norm, crossCheck=False)
        settings[algorithm] = dict(nfeatures=1500, other_parameters="OpenCV defaults",
                                   target_keypoints=len(ref_kp), norm="HAMMING" if algorithm == "ORB" else "L2")
        write_image(OUTPUT / "keypoints" / f"{algorithm}_target.png",
                    cv2.drawKeypoints(reference, ref_kp, None, color=(0, 255, 0)))
        for (slug, label, number, _), roi in zip(SELECTIONS, crops):
            scene = matching_image(roi)
            keypoints, descriptors = detector.detectAndCompute(scene, None)
            # Query = condition crop; reference = target. Deduplicate target indices.
            matches = [] if descriptors is None else unique_ratio_matches(matcher, descriptors, ref_desc, RATIO)
            rate = 100 * len(matches) / len(keypoints) if keypoints else 0.0
            rows.append(dict(algorithm=algorithm, condition=label, frame=number,
                             extracted_keypoints=len(keypoints), matched_keypoints=len(matches),
                             match_rate_percent=round(rate, 2), target_keypoints=len(ref_kp)))
            write_image(OUTPUT / "keypoints" / f"{algorithm}_{slug}.png",
                        cv2.drawKeypoints(scene, keypoints, None, color=(0, 255, 0)))
            drawn = cv2.drawMatches(scene, keypoints, reference, ref_kp, matches, None,
                                   matchColor=(0, 255, 0), singlePointColor=(0, 0, 255),
                                   flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
            write_image(OUTPUT / "matches" / f"{algorithm}_{slug}_{number:04d}.png", drawn)
            pairs = [dict(condition_keypoint=m.queryIdx, target_keypoint=m.trainIdx,
                          condition_xy=list(keypoints[m.queryIdx].pt),
                          target_xy=list(ref_kp[m.trainIdx].pt), distance=m.distance) for m in matches]
            (OUTPUT / "matches" / f"{algorithm}_{slug}_{number:04d}.json").write_text(json.dumps(pairs, indent=2) + "\n")

    with (OUTPUT / "metrics.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    settings.update(opencv=cv2.__version__, resize_scale=SCALE, interpolation="INTER_CUBIC",
                    grayscale=True, ratio_test=RATIO, query="condition GT crop", train="target GT crop",
                    uniqueness="best distance per target descriptor", geometric_verification=False,
                    rate_denominator="condition crop keypoints", video_playback_fps=25 if args.video else None)
    (OUTPUT / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    report = ["# Jogging-1 ORB / SIFT 특징점 매칭", "",
              "GT: `groundtruth_rect.1.txt`. target: 0001번. 프레임 번호는 원본 JPG의 1-based 번호.", "",
              "307개 원본 프레임을 확인해 선정했다. 30°/60°는 얼굴·어깨 방향의 근사 구간, 30%/50%는 몸 실루엣 가림의 육안 근사값이다. 정밀한 각도·가림률 실험이나 순수 회전 실험은 아니며 달리기 자세·크기·배경도 달라진다.", "",
              "원본 GT bbox 크롭은 `data/matching_inputs/Jogging-1/`의 target.png와 조건별 PNG에 보존했다. 특징점 검출에는 모두 회색조+4배 INTER_CUBIC 확대를 적용했다. 좁은 크롭에서 ORB 기본 31픽셀 경계 제외로 특징점이 사라지는 문제를 피하기 위한 동일 전처리이며, 확대가 실제 영상 세부 정보를 추가하지는 않는다.", "",
              "BF kNN(k=2), Lowe ratio < 0.75, target 특징점 중복 제거. 추출 수는 각 조건 크롭의 특징점 수, 매칭률 = 매칭 수 / 해당 조건 추출 수 × 100. 매칭 수는 이 규칙을 통과한 대응 수이며 기하 검증된 정답 수가 아니다. GT bbox의 배경과 가림 물체 특징도 포함되므로 사람 인식 정확도로 해석하지 않는다.", ""]
    for algorithm in ("ORB", "SIFT"):
        report += [f"## {algorithm}", "", f"target 특징점: {settings[algorithm]['target_keypoints']}개", "",
                   "| 조건 | 프레임 | 추출된 특징점 수 | 매칭된 특징점 수 | 매칭률 |",
                   "|---|---:|---:|---:|---:|"]
        for row in rows:
            if row["algorithm"] == algorithm:
                report.append(f"| {row['condition']} | {row['frame']} | {row['extracted_keypoints']} | {row['matched_keypoints']} | {row['match_rate_percent']:.2f}% |")
        report.append("")
    report += ["## 재현", "", "`python -m scripts.data.prepare_jogging_matching --video`", "",
               "실험 입력 PNG와 관찰용 MP4: `data/matching_inputs/Jogging-1/`. 원본 JPG·GT·선정 근거: `data/matching_assets/Jogging-1/`.",
               "`inspection/`: 전체 307프레임 GT 미리보기. `selected_preview.png`: 선정 크롭 모음. `matches/`: 조건(왼쪽)과 target(오른쪽)의 매칭 그림·좌표. `keypoints/`: 특징점 그림. `data/matching_assets/Jogging-1/selection.json`에 선정 근거·GT·원본 해시, `settings.json`에 실험 설정을 기록했다.",
               "MP4의 25 fps는 관찰용 재생 속도이며 원본 촬영 FPS를 주장하지 않는다.", ""]
    (OUTPUT / "report.md").write_text("\n".join(report))
    if args.video:
        writer = cv2.VideoWriter(str(INPUTS / "jogging.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 25, (352, 288))
        if not writer.isOpened():
            raise OSError("Could not create jogging.mp4")
        try:
            for image in images:
                writer.write(image)
        finally:
            writer.release()
    print((OUTPUT / "report.md").read_text())


if __name__ == "__main__":
    main()

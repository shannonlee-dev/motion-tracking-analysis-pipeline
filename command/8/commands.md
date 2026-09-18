# `data/tracking_inputs/08.mp4` 실행 명령

레포지토리 루트에서 실행합니다.

## 기본 GUI 실행
```bash
./.venv/bin/python app.py --source data/tracking_inputs/08.mp4
```

## 전경 마스크와 함께 GUI 실행
```bash
./.venv/bin/python app.py --source data/tracking_inputs/08.mp4 --show-mask
```

## Headless 실행: 분석 MP4와 추적 CSV 저장
```bash
./.venv/bin/python app.py --source data/tracking_inputs/08.mp4 --headless --output command/8/08_result.mp4 --csv command/8/08_tracking.csv
```

## 처리 프레임 수 제한
```bash
./.venv/bin/python app.py --source data/tracking_inputs/08.mp4 --headless --max-frames 300 --output command/8/08_first_300.mp4 --csv command/8/08_first_300.csv
```

## 추적 옵션
```bash
./.venv/bin/python app.py --source data/tracking_inputs/08.mp4 --headless --output command/8/08_velocity.mp4 --csv command/8/08_velocity.csv --predict-velocity
./.venv/bin/python app.py --source data/tracking_inputs/08.mp4 --headless --output command/8/08_tuned.mp4 --csv command/8/08_tuned.csv --learning-rate 0.01 --min-area 80 --max-distance 50 --kernel-size 3 --max-missing 15 --warmup-frames 25
```

## 등록 대상 매칭
```bash
TARGET_IMAGE=data/matching_assets/Jogging-1/selected_frames/target.png
./.venv/bin/python app.py --source data/tracking_inputs/08.mp4 --target "$TARGET_IMAGE" --headless --output command/8/08_target.mp4 --csv command/8/08_target.csv
```

## 스냅샷과 전체 옵션
```bash
./.venv/bin/python app.py --source data/tracking_inputs/08.mp4 --snapshot-dir command/8/snapshots
./.venv/bin/python -m motion_tracking --help
```

다음 설정은 서로 조합할 수 있습니다: `--learning-rate`, `--min-area`, `--max-distance`, `--kernel-size`, `--max-missing`, `--warmup-frames`, `--predict-velocity`, `--target`, `--output`, `--csv`, `--max-frames`, `--snapshot-dir`.

## 영상별 추천 설정

전체 프레임 스윕 기준 추천값입니다. 접촉 장면에서 작은 조각까지 놓치지 않도록 설정합니다.

```bash
./.venv/bin/python app.py --source data/tracking_inputs/08.mp4 --show-mask --learning-rate 0.005 --min-area 50 --kernel-size 1 --max-distance 80 --max-missing 30 --predict-velocity
```
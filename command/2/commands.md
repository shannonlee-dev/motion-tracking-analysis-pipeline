# `data/tracking_inputs/02.mpg` 실행 명령

레포지토리 루트에서 실행합니다.

## 기본 GUI 실행
```bash
./.venv/bin/python app.py --source data/tracking_inputs/02.mpg
```

## 전경 마스크와 함께 GUI 실행
```bash
./.venv/bin/python app.py --source data/tracking_inputs/02.mpg --show-mask
```

## Headless 실행: 분석 MP4와 추적 CSV 저장
```bash
./.venv/bin/python app.py --source data/tracking_inputs/02.mpg --headless --output command/2/02_result.mp4 --csv command/2/02_tracking.csv
```

## 처리 프레임 수 제한
```bash
./.venv/bin/python app.py --source data/tracking_inputs/02.mpg --headless --max-frames 300 --output command/2/02_first_300.mp4 --csv command/2/02_first_300.csv
```

## 추적 옵션
```bash
./.venv/bin/python app.py --source data/tracking_inputs/02.mpg --headless --output command/2/02_velocity.mp4 --csv command/2/02_velocity.csv --predict-velocity
./.venv/bin/python app.py --source data/tracking_inputs/02.mpg --headless --output command/2/02_tuned.mp4 --csv command/2/02_tuned.csv --learning-rate 0.01 --min-area 80 --max-distance 50 --kernel-size 3 --max-missing 15 --warmup-frames 25
```

## 등록 대상 매칭
```bash
TARGET_IMAGE=data/matching_assets/Jogging-1/selected_frames/target.png
./.venv/bin/python app.py --source data/tracking_inputs/02.mpg --target "$TARGET_IMAGE" --headless --output command/2/02_target.mp4 --csv command/2/02_target.csv
```

## 스냅샷과 전체 옵션
```bash
./.venv/bin/python app.py --source data/tracking_inputs/02.mpg --snapshot-dir command/2/snapshots
./.venv/bin/python -m motion_tracking --help
```

다음 설정은 서로 조합할 수 있습니다: `--learning-rate`, `--min-area`, `--max-distance`, `--kernel-size`, `--max-missing`, `--warmup-frames`, `--predict-velocity`, `--target`, `--output`, `--csv`, `--max-frames`, `--snapshot-dir`.

## 영상별 추천 설정

전체 프레임 스윕 기준 추천값입니다. 정지·느린 이동 구간에서 배경 흡수를 줄이는 설정입니다.

```bash
./.venv/bin/python app.py --source data/tracking_inputs/02.mpg --show-mask --learning-rate 0.0005 --min-area 80 --kernel-size 1 --max-distance 80 --max-missing 30 --predict-velocity
```
# `data/tracking_inputs/01.mpg` 실행 명령

레포지토리 루트에서 실행합니다. 가상환경을 활성화했다면 `./.venv/bin/python` 대신 `python`을 사용해도 됩니다.

## 기본 GUI 실행

```bash
./.venv/bin/python app.py --source data/tracking_inputs/01.mpg
```

## 전경 마스크와 함께 GUI 실행

```bash
./.venv/bin/python app.py --source data/tracking_inputs/01.mpg --show-mask
```

## Headless 실행: 분석 MP4와 추적 CSV 저장

```bash
./.venv/bin/python app.py --source data/tracking_inputs/01.mpg --headless --output command/1/01_result.mp4 --csv command/1/01_tracking.csv
```

## 처리 프레임 수 제한

```bash
./.venv/bin/python app.py --source data/tracking_inputs/01.mpg --headless --max-frames 300 --output command/1/01_first_300.mp4 --csv command/1/01_first_300.csv
```

## 추적 옵션

```bash
./.venv/bin/python app.py --source data/tracking_inputs/01.mpg --headless --output command/1/01_velocity.mp4 --csv command/1/01_velocity.csv --predict-velocity
./.venv/bin/python app.py --source data/tracking_inputs/01.mpg --headless --output command/1/01_tuned.mp4 --csv command/1/01_tuned.csv --learning-rate 0.01 --min-area 80 --max-distance 50 --kernel-size 3 --max-missing 15 --warmup-frames 25
```

## 등록 대상 매칭

실행 전에 `TARGET_IMAGE`에 등록 이미지 경로를 지정합니다.

```bash
TARGET_IMAGE=data/matching_assets/Jogging-1/selected_frames/target.png
./.venv/bin/python app.py --source data/tracking_inputs/01.mpg --target "$TARGET_IMAGE" --headless --output command/1/01_target.mp4 --csv command/1/01_target.csv
```

## 스냅샷과 전체 옵션

```bash
./.venv/bin/python app.py --source data/tracking_inputs/01.mpg --snapshot-dir command/1/snapshots
./.venv/bin/python -m motion_tracking --help
```

다음 설정은 서로 조합할 수 있습니다: `--learning-rate`, `--min-area`, `--max-distance`, `--kernel-size`, `--max-missing`, `--warmup-frames`, `--predict-velocity`, `--target`, `--output`, `--csv`, `--max-frames`, `--snapshot-dir`.

## 영상별 추천 설정

전체 프레임 스윕 기준 추천값입니다. 작은 검출 조각은 줄이고 주인공 검출을 유지하는 균형값입니다.

```bash
./.venv/bin/python app.py --source data/tracking_inputs/01.mpg --show-mask --learning-rate 0.001 --min-area 80 --kernel-size 1 --max-distance 80 --max-missing 30 --predict-velocity
```


## 마지막에 오른쪽으로 들어가는 사람 MISSING 후 부활

 ./.venv/bin/python app.py   --source data/tracking_inputs/01.mpg   --show-mask   --learning-rate 0.01   --min-area 20   --kernel-size 1   --max-distance 80   --max-missing 30 \
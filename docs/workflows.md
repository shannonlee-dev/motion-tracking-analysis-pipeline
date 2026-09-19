# 실행과 재현

프로젝트 루트에서 가상환경을 활성화한 뒤 복사해 실행한다. 준비·평가 스크립트 자체는 다른 작업 디렉토리에서도 저장소 경로를 찾는다. 앱에 직접 주는 상대 경로와 `--output-dir` 상대 경로는 현재 작업 디렉토리 기준이다.

## 데이터 준비

```bash
python scripts/01_setup_data.py
python scripts/02_verify_data.py
```

정상 입력은 해시를 검증하고 그대로 사용한다. 원본 archive는 `data/<목적>/raw`, 데이터 주석·출처·고정 해시는 `reference`, 사용 입력은 `inputs`, 자동 상태 manifest는 `generated`에 둔다. 기존 해시를 현재 파일 값으로 덮어쓰지 않는다. 손상된 입력은 오류로 알리므로 잘못된 파일을 별도로 옮긴 뒤 재실행한다.

- `--offline`: 네트워크 없이 로컬 준비·복원. 누락된 원본은 명확한 오류로 종료한다.
- `--purpose tracker|matcher|detection`: 해당 데이터만 준비·검증. 기본은 전체다.
- `--raw`: Tracker 원본 다운로드·압축 해제 및 GT를 준비한다. 아래 학습률 픽셀 실험에 필요하다.
- Oxford: `aria2c`가 없으면 `--detection-source /path/to/TownCentreXVID.mp4`로 기존 다운로드를 가져온다. 원본·등록 crop·결과 영상은 Git 제외다. 등록 좌표는 `data/detection/reference/source.json`에 보존했다.

Tracker 04–11과 14의 과거 H.264 인코더 설정은 기록되지 않았다. 보존된 입력은 바이트 단위로 검증한다. 입력을 삭제하고 원본에서 재구성하면 같은 프레임 구간을 mp4v로 생성하고, 다른 바이트 해시와 코덱을 `data/tracker/generated/inputs.json`에 기록한다. 이 경우 과거 측정과 같다고 가정하지 말고 평가를 다시 실행한다. 새 클론은 보존 입력을 사용하므로 이 재인코딩이 필요 없다.

## 실제 앱과 보고서 실험

```bash
# 단일 입력 → 기본 설정 → MP4·CSV
python app.py --source data/tracker/inputs/01.mpg
# 모든 입력 → 각 40프레임 smoke test
# 원본 GT 준비 → 전체 주석 평가 + 세 learning-rate 실험
python scripts/01_setup_data.py --purpose tracker --raw
python -m experiments.tracker_metrics
python -m experiments.learning_rate
```

기본 결과는 `results/tracker/runs/latest/case_XX/{video.mp4,tracks.csv}`다.
`--measure`는 `submission/`에 네 가지 Tracker 설정의 원본 trace·사건 30개 집계·검토 시트를,
`learning_rate/`에 17번 영상의 0.001·0.01·0.1 측정 및 GT 픽셀 비교를 쓴다.
12·13은 기존 사건 주석 프로토콜 대상이 아니며 `--suite` 앱 실행에는 포함된다.
측정 정의·제외 후보·수동 검토 한계는 [보고서](report.md)에 있다.

개별 파라미터 실험은 앱 CLI를 사용한다. 이전 추천값과 관찰 메모는 [Tracker 설정 기록](recipes/tracker.md)에 보존했다.

```bash
python app.py --source data/tracker/inputs/17.mp4 --headless --learning-rate 0.001 \
  --output results/tracker/runs/lr_0001/video.mp4 --csv results/tracker/runs/lr_0001/tracks.csv
```

## 특징점 실험

```bash
python -m experiments.feature_matching
```

`results/matcher/runs/latest/roi/`: ORB/SIFT 각 5조건, keypoint·match 그림과 좌표, metrics.csv, settings.json.
`application/`: 같은 선정 시점에 대한 기존 전체 프레임 ORB 비교. ROI 조건→target 매칭과 앱 target→전체 프레임 매칭은 다른 실험이다. ROI 매칭률을 사람 검출 정확도로 해석하지 않는다. 각도·가림률은 육안 근사 구간이다.

## Oxford Target Detection 시연

```bash
python app.py --source data/detection/raw/town_centre.mp4 --target data/detection/inputs/target.png
```

`results/detection/runs/latest/{video.mp4,tracks.csv,summary.json}`에 전체 프레임 앱 결과를 저장한다.
`target_frames > 0`을 성공 조건으로 확인한다. 이는 등록 이미지 인식 시연이며 독립적인 인식 정확도 평가가 아니다.
모든 평가에서 `--output-dir`로 새 결과 위치를 지정할 수 있다. `baseline` 덮어쓰기는 거부한다.

## GUI와 출력

`q`: 종료, `p`: 일시정지/재개, `s`: 현재 화면을 `--snapshot-dir`에 저장.
타임라인 seek는 MOG2 배경 모델과 ID를 초기화한다. CSV에는 원본 frame 번호가 기록되므로 seek 후 번호가 연속되지 않을 수 있다.
기본 스냅샷은 `results/tracker/runs/manual/snapshots/`다. Detection GUI에서는 `--snapshot-dir results/detection/runs/manual/snapshots`를 지정한다.

# Motion Tracking Analysis Pipeline

## 프로젝트 소개

OpenCV MOG2로 움직임을 검출하고 거리 기반 Tracker로 객체의 ID·궤적을 추적합니다.
ORB로 등록 물체를 재인식하며 겹침·정지·조명 변화의 한계를 측정합니다. 딥러닝·`cv2.dnn`·MediaPipe는 사용하지 않습니다.

## 핵심 특징

- 웹캠·영상 입력, 박스·ID·중심점·궤적·처리 FPS 표시
- 등록 이미지 인식 시 `TARGET DETECTED` 표시, q/p/s 키 제어
- 화면 없는 분석과 선택적 MP4·CSV 저장
- 추적 30회, 학습률 3종, 특징점 5조건 및 실제 영상 평가

## 아키텍처

실행 흐름은 `app.py → cli.main → runner.run → MotionDetector → Tracker → draw_overlay`입니다.
등록 이미지가 있으면 같은 프레임에 `TargetMatcher`를 실행합니다. CLI는 옵션 해석,
`runner.run()`은 영상 입출력·프레임 루프를 담당합니다.

```text
.
├── app.py                   # CLI 진입점
├── motion_tracking/         # 재사용 가능한 앱 코드
│   ├── __init__.py
│   ├── __main__.py          # python -m motion_tracking
│   ├── cli.py               # CLI 옵션·오류 메시지
│   ├── runner.py            # 영상 입력 → 검출·추적 → 표시·MP4·CSV
│   ├── config.py            # 알고리즘 기본값·검증
│   ├── vision.py            # MOG2 검출·ORB 재인식
│   ├── tracker.py           # 거리 매칭·ID·궤적
│   ├── display.py           # 오버레이·키 제어
│   └── evaluation.py        # 정답 연결·추적 지표
├── scripts/                 # 프로젝트 데이터·실험 도구
│   ├── __init__.py
│   ├── common.py            # 프로젝트 경로·CSV 저장
│   ├── data/
│   │   ├── __init__.py
│   │   ├── download.py      # CAVIAR 다운로드
│   │   ├── prepare.py       # ALOI·LASIESTA 준비
│   │   ├── caviar.py        # XML 정답 로더
│   │   ├── lasiesta.py      # 프레임·정답 짝 확인, 픽셀 라벨
│   │   └── synthetic.py     # 합성 프레임·정답·표적 영상 생성
│   └── eval/
│       ├── __init__.py
│       ├── run.py           # 통제 실험 실행·결과 집계
│       ├── tracking.py      # 합성·CAVIAR 추적 평가
│       ├── synthetic.py     # 합성 특징점·배경 실험
│       ├── aloi.py          # ALOI ORB·SIFT 비교
│       ├── lighting.py      # LASIESTA 조명 평가
│       └── natural_events.py # LASIESTA 가림·정지 평가
├── tests/                   # 알고리즘·실험·CLI·영상 출력 회귀 테스트
├── data/                    # 원본·출처·이용 조건
├── results/                 # 측정 CSV·로그·영상·캡처
├── docs/                    # 분석 보고서·검토 기록
├── requirements.txt         # 실행 의존성
└── requirements-dev.txt     # 테스트 의존성
```

앱 코드는 `scripts/`에 의존하지 않습니다. 평가 스크립트는 `motion_tracking/`의 알고리즘과
`scripts/data/`의 입력 함수를 직접 조합합니다. Python에서 영상을 분석할 때는
`from motion_tracking.runner import run`을 사용합니다. 데이터를 읽으려면 `scripts/data/`, 알고리즘을 바꾸려면
`motion_tracking/`, 평가 조건을 바꾸려면 `scripts/eval/`부터 확인합니다.

## 실행과 설정

Python 3.11 이상, 프로젝트 루트에서 실행합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m scripts.data.download  # CAVIAR 원본이 없을 때
python app.py --source data/raw/meeting.mpg --show-mask
```

Windows 활성화 명령은 `.venv\Scripts\activate`입니다. `q`는 종료, `p`는 정지·재개, `s`는 PNG 저장입니다.

| 옵션 | 용도·기본값 |
| --- | --- |
| `--source` | 영상 경로 또는 웹캠 번호(기본 `0`) |
| `--target` | 등록 이미지 경로 |
| `--learning-rate` / `--min-area` | 배경 학습률 `0.01` / 최소 검출 면적 `80px²` |
| `--kernel-size` | 열림·닫힘 커널 크기 `3` |
| `--max-distance` / `--max-missing` | 연결 거리 `50px` / ID 보존 누락 `15프레임` |
| `--headless` / `--output` / `--csv` | 창 없이 실행 / MP4 경로 / CSV 경로 |

기본값은 `motion_tracking/config.py`에서 수정하거나 CLI로 덮어씁니다. 전체 옵션은 `python app.py --help`로 확인합니다. `python -m motion_tracking`도 같은 옵션을 받습니다.
표시 FPS는 원본 FPS가 아닌 처리 속도입니다.

```bash
python app.py --source data/raw/meeting.mpg --headless \
  --output results/videos/meeting.mp4 --csv results/traces/meeting.csv
```

## 평가와 결과

```bash
python -m scripts.data.prepare        # ALOI 물체 1개·LASIESTA 5개 준비
python -m scripts.eval.run            # 합성 30회 × 8설정·CAVIAR 3개
python -m scripts.eval.aloi           # 동일 물체 5조건·조명, ORB/SIFT 비교
python -m scripts.eval.lighting       # LASIESTA 조명 2개
python -m scripts.eval.natural_events # LASIESTA 가림·정지 3개
python -m pytest -q
```

RAR 해제에는 OS libarchive와 `python -m pip install libarchive-c`가 필요합니다. ALOI 1,000개 전수평가는 제외합니다.
`run`·`natural_events`에 `--export-videos`를 추가하면 관찰 영상도 저장합니다.

| 결과 위치 | 내용 |
| --- | --- |
| `results/tracking_trials.csv` / `tracking_summary.csv` / `synthetic_objects.csv` | 합성 시험별·조건별·물체별 추적 결과 |
| `results/background.csv` / `features.csv` / `aloi_features.csv` | 학습률·특징점 비교 |
| `results/current/` | CAVIAR·LASIESTA 측정 CSV, `traces/`·`captures/`·`videos/` |
| `results/run.json` | `scripts.eval.run` 실행 환경·설정·소요 시간 |

SIFT는 `scripts/eval/aloi.py`의 `main()`에서 `cv2.SIFT_create(nfeatures=1500)`·`detectAndCompute`·L2 kNN(k=2)·ratio 0.75·중복 제거·RANSAC(3px)으로 비교합니다.
`aloi_features.csv`의 `SIFT_reference`는 대응점·인라이어 참고값이며 `found`는 비워 둡니다. 앱은 ORB를 사용합니다.

[분석 보고서](docs/report.md)에 필수 평가표·측정 기준·한계·수동 검토 절차가 있습니다.
[검토 기록](docs/review.csv)의 사람 수동 전수계수는 미완료이며, 실물 웹캠·실제 가림 비율·일부 GT 정렬도 미검증입니다.
보고서와 검토 기록은 재실행으로 자동 갱신되지 않습니다.

출처·이용 조건·공개 범위는 [데이터 안내](data/NOTICE.md), 원본 해시는 각 `sources.json`에 있습니다.
`data/download/`는 반입 원본 보관소이며, ALOI 이미지와 과제 원문은 재배포 허가 미확인으로 공개에서 제외합니다.

![실제 영상 추적 화면](results/captures/meeting_demo_preview.jpg)

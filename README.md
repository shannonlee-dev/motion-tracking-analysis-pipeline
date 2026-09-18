# Motion Tracking Analysis Pipeline

## 프로젝트 소개

OpenCV MOG2로 움직임을 검출하고 거리 기반 Tracker로 객체의 ID·궤적을 추적하는 Python 앱입니다.
ORB 특징점 매칭으로 등록 물체를 재인식합니다. 딥러닝·cv2.dnn·MediaPipe는 사용하지 않습니다.
추적 성능과 한계는 결과 영상을 직접 관찰하고 수동으로 기록합니다.

## 핵심 특징

- 웹캠·영상 입력, 박스·ID·중심점·궤적·처리 FPS·프레임 번호 표시
- 파일 영상 GUI의 타임라인 막대로 원하는 프레임 탐색
- 등록 이미지 인식 시 `TARGET DETECTED` 표시
- q 종료, p 일시정지·재개, s 스냅샷 저장
- 화면 없는 실행과 선택적 MP4·추적 CSV 저장

## 아키텍처

```text
app.py                 # CLI 진입점
motion_tracking/
├── __main__.py        # python -m motion_tracking
├── cli.py             # 옵션 해석·오류 메시지
├── runner.py          # 영상 입출력·프레임 루프·저장
├── config.py          # 알고리즘 설정·검증
├── vision.py          # MOG2 검출·ORB 재인식
├── tracker.py         # 거리 매칭·ID·궤적
├── display.py         # 오버레이·키 제어
├── features.py        # 특징점 매칭
├── geometry.py        # 박스 좌표 타입
└── constants.py       # 영상·출력 관련 상수
tests/                # 앱 회귀 테스트
data/                 # 관찰용 입력 자료·출처
results/              # 실제 영상 분석 결과와 새 실행 출력
docs/                 # 수동 확인·기록 문서
```

`cli.main → runner.run → MotionDetector → Tracker → draw_overlay` 순서로 실행합니다.
등록 이미지가 있으면 `TargetMatcher`가 같은 프레임에서 별도로 물체를 찾습니다.
Python에서는 `from motion_tracking.runner import run`으로 호출할 수 있습니다.

## 실행과 설정

Python 3.11 이상, 프로젝트 루트에서 실행합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py --source data/tracking_inputs/caviar/single_1_overlap_1.mpg --show-mask
```

Windows 활성화 명령은 `.venv\Scripts\activate`입니다.
`python -m motion_tracking`도 같은 옵션을 받습니다.

| 옵션 | 용도·기본값 |
| --- | --- |
| `--source` | 영상 경로 또는 웹캠 번호, 기본 `0` |
| `--target` | 등록할 물체 이미지 경로 |
| `--learning-rate` / `--min-area` | 배경 학습률 `0.01` / 최소 검출 면적 `80px²` |
| `--kernel-size` | 열림·닫힘 커널 크기 `3` |
| `--max-distance` / `--max-missing` | 연결 거리 `50px` / ID 보존 누락 `15프레임` |
| `--warmup-frames` | 초기 배경 학습 `25프레임` |
| `--predict-velocity` | 속도 기반 위치 예측 사용 |
| `--headless` / `--output` / `--csv` | 창 없이 실행 / MP4 경로 / 추적 CSV 경로 |

전체 옵션은 `python app.py --help`로 확인합니다. 화면 FPS는 원본 영상 FPS가 아닌 처리 속도입니다.
파일 영상을 GUI로 열면 창 아래 `Timeline (frame)` 막대가 표시됩니다. 막대를 옮기면 해당 프레임부터
배경 모델과 추적 ID를 새로 시작합니다. 웹캠과 `--headless` 실행에는 막대가 표시되지 않습니다.

```bash
python app.py --source data/tracking_inputs/caviar/single_1_overlap_1.mpg --headless \
  --output results/caviar/videos/single_1_overlap_1.mp4 --csv results/caviar/traces/single_1_overlap_1.csv
```

## 수동 확인과 보고서

[수동 확인·기록 문서](docs/report.md)에 기능 체크리스트, 측정 기준과 작성할 표가 있습니다.
20~30초 영상에서 단일 이동·겹침 각 10회, 정지·조명 변화 각 5회 이벤트를 관찰합니다.
저장 영상의 프레임 번호를 확인하며 ID Switch·추적 실패를 직접 세고 조건별 실패율을 기록합니다.
추적 CSV는 프레임별 앱 출력이며 정답이나 자동 채점 결과가 아닙니다.
기존 참고 영상·캡처는 [결과물 안내](results/README.md)에 정리했습니다. 수동 검증 완료 자료는 아닙니다.

관찰용 원본 자료는 `data/tracking_inputs/`에 있습니다. 출처와 이용 조건은 `data/NOTICE.md`를 확인합니다.

## 데이터 준비

```bash
python -m scripts.data.prepare_caviar  # CAVIAR·추가 조명 원본 다운로드
python -m pip install libarchive-c
python -m scripts.data.prepare_lasiesta   # LASIESTA 다운로드·RAR 해제
```

RAR 해제에는 OS libarchive도 필요합니다. CAVIAR·추가 조명 원본과 LASIESTA 원본 RAR·해제본은
`data/raw/`에 저장하며 Git에서 제외합니다. 이름을 정리한 관찰용 입력은 `data/tracking_inputs/`에, 다운로드 manifest는 `data/manifests/`에 둡니다. 합성 영상 생성과 자동 평가는 포함하지 않습니다.

## 개발 검증

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

테스트는 검출·추적·특징점 매칭과 CLI·영상 저장·키 제어의 회귀를 확인합니다.
과제의 수동 성능 측정은 별도로 진행합니다.

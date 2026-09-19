# Motion Tracking Analysis Pipeline

## 프로젝트 소개

OpenCV MOG2로 움직임을 검출하고 객체 ID·궤적을 추적하는 Python 앱입니다.
등록 이미지는 ORB로 전체 프레임에서 찾습니다. 딥러닝은 사용하지 않습니다.

## 핵심 특징

| 평가 목적 | 데이터 | 확인 항목 |
| --- | --- | --- |
| **Tracker Test** | 01–19: CAVIAR·LASIESTA·조명 영상 | MOG2, bbox, ID·궤적, ID switch·추적 실패, learning rate |
| **Matcher Test** | OTB Jogging | ORB/SIFT 특징점·매칭률, 회전·가림 조건의 ROI 비교 |
| **Target Detection Test** | Oxford Town Centre | 실제 앱 전체 프레임 TargetMatcher, 특정 사람 등록, `TARGET DETECTED` 시연 |

웹캠·영상, GUI 타임라인, headless 실행, MP4·CSV 저장을 지원합니다.
`q` 종료, `p` 일시정지·재개, `s` 스냅샷. 탐색하면 MOG2와 추적 ID를 초기화합니다.

## 아키텍처

```text
app.py / motion_tracking/     # CLI, 영상 루프, 검출, 추적, 매칭, 화면
scripts/                     # 데이터 준비 2단계 + 평가 진입점
datasets/                    # 다운로드·검증·변환·등록 이미지
evaluation/                  # 앱 알고리즘을 사용하는 별도 실험 코드
data/{tracker,matcher,detection}/
  reference/                 # 출처 manifest, 원본 주석, 고정 실험 조건
  raw/                       # 로컬 원본 다운로드·압축 해제 (Git 제외)
  inputs/                    # 앱·평가 입력
  generated/                 # 준비 상태·재구성 이력 (Git 제외)
results/{tracker,matcher,detection}/
  baseline/                  # 보존한 기존 측정 자료 (tracker, matcher)
  runs/                      # 새 실행 결과 (Git 제외)
docs/                        # 실행 지침, 분석 보고서, 이전 기록
```

## 설치

Python 3.11 이상. 저장소 루트에서 실행합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows에서는 `.venv\Scripts\activate`로 활성화합니다.
원본 RAR 재구성에는 OS `libarchive`, Oxford 자동 다운로드에는 `aria2c`가 필요합니다.
이미 보존된 입력이 정상이라면 다시 다운로드하거나 변환하지 않습니다.

## 데이터 준비

```bash
python scripts/01_setup_data.py
python scripts/02_prepare_evaluation.py
```

첫 단계는 고정 해시 검증·필요한 다운로드/압축 해제/변환·등록 이미지·manifest를 준비합니다.
두 번째는 영상 전체 디코딩, 평가 주석, 앱 등록 이미지까지 검사합니다.
Oxford 원본을 이미 받았다면 첫 명령에 `--detection-source /path/to/TownCentreXVID.mp4`를 지정합니다.
오프라인 재검사는 `--offline`, 한 목적만 준비하려면 `--purpose tracker|matcher|detection`을 사용합니다.
출처·재배포 제한은 [data/NOTICE.md](data/NOTICE.md)를 따릅니다. Oxford 원본·파생물은 로컬 전용입니다.

## 앱 실행

```bash
python app.py --source data/tracker/inputs/01.mpg --show-mask
python app.py --source data/detection/raw/town_centre.mp4 --target data/detection/inputs/target.png
python app.py --help
```

화면이 없는 환경에서는 `--headless`를 추가합니다. 처리 FPS는 원본 재생 FPS와 다릅니다.

## 평가 실행

```bash
python scripts/evaluate.py tracker --case 1 --max-frames 100
python scripts/evaluate.py matcher
python scripts/evaluate.py detection
```

Tracker 전체 입력은 `--suite`, 기존 주석·학습률 실험 전체 재현은 [실행 지침](docs/workflows.md)을 참조합니다.
Detection 기본 실행은 Oxford 전체 영상입니다. 등록 프레임이 5800이므로 짧은 앞부분만 실행하면 대상이 나오지 않을 수 있습니다.

결과: `results/<목적>/runs/latest/`. 이전 측정: `results/{tracker,matcher}/baseline/`.
[분석 보고서](docs/report.md), [실험별 설정](docs/recipes/tracker.md), [구조·이전 기록](docs/migration.md).

## 개발 검증

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
```

단위·회귀 테스트와 실제 데이터 측정 재현은 별개입니다. 추적 실패 집계의 수동 검토 한계는 보고서에 명시했습니다.

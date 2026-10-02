# Motion Tracking Analysis Pipeline

## 프로젝트 소개

OpenCV MOG2로 움직임을 검출하고 객체 ID·궤적을 추적하는 Python 앱입니다.
등록 대상은 별도의 전체 프레임 SIFT 매칭으로 찾습니다. 딥러닝은 사용하지 않습니다.

## 핵심 특징

- 웹캠·영상 입력, GUI 타임라인, 마스크 표시, headless 실행, MP4·CSV 저장
- 추적·학습률·대상 매칭을 실제 앱 경로로 평가하고 측정 근거 보존
- 전경 조각 재구성 실험 지원. 교차·가림 회귀가 있어 **기본 비활성화**

현재 구조로 신체 분리·정지·사람 간 겹침을 함께 안정적으로 해결하지 못했습니다.
측정 결과와 한계는 [분석 보고서](docs/report.md)에 정리했습니다.

## 아키텍처

| 구성 요소 | 역할 |
| --- | --- |
| `src/motion_tracking/cli.py`, `config.py` | 입력·출력 옵션과 기존 알고리즘 설정 |
| `motion.py`, `tracker.py`, `matching.py`, `features.py` | MOG2 검출, 객체 추적, SIFT 대상 매칭 |
| `runner.py`, `display.py` | 프레임 처리, GUI 제어, MP4·CSV 저장 |
| `src/motion_tracking/datasets/` | 원본 확보, 체크섬 검증, GT·영상 준비 |
| `src/motion_tracking/experiments/` | 실제 앱 결과를 이용한 실험·평가 |
| `data/`, `docs/evidence/` | 라이선스·원본 데이터·고정 측정 근거 보존 |

```mermaid
flowchart TD
    Setup["motion_tracking.datasets<br/>데이터 준비·검증"] --> Data["data/<br/>영상·등록 이미지·GT"]
    Data -- "영상" --> App["motion-tracking → cli.py → runner.run()"]
    Camera["웹캠"] --> App
    Config["config.py<br/>기본값·CLI 설정"] --> App

    subgraph Pipeline["src/motion_tracking/ · 프레임 처리"]
        Frame["입력 프레임"] --> Motion["motion.py<br/>MOG2 → 이진화 → OPEN/CLOSE → bbox"]
        Motion --> Compose{"조각 재구성 활성화?"}
        Compose -- "예" --> Group["tracker.py · compose()<br/>이전 객체 범위로 조각 구성"]
        Compose -- "아니요 · 기본" --> Track["tracker.py · update()<br/>중심점 대응 → ID·궤적"]
        Group --> Track
        Track -. "이전 프레임 bbox" .-> Group
        Frame --> Match["matching.py + features.py<br/>등록 대상 SIFT 매칭 · 선택"]
    end

    App --> Frame
    Data -. "등록 이미지" .-> Match
    Track --> Output["display.py + runner.py<br/>화면·MP4·CSV"]
    Match --> Output
    App -. "프레임별 결과 제공" .-> Eval["motion_tracking.experiments<br/>GT 비교·집계·시각화"]
    Data -. "GT" .-> Eval
    Eval --> Results["results/ · 새 실행 결과"]
    Results -. "검토 후 보존" .-> Evidence["docs/evidence/ · 고정 측정 근거"]
```

검출·추적·SIFT는 앱에만 구현합니다. `src/motion_tracking/experiments/`는 같은 `runner.run()`의 결과를 평가합니다.
SIFT 매칭은 추적 ID와 독립적이며 전경 마스크를 보정하지 않습니다.

## 설치·데이터 준비

Python 3.13과 uv를 사용합니다. 저장소 루트에서 실행합니다.

```bash
make setup
uv run --frozen motion-data-setup
uv run --frozen motion-data-verify
```

원본 RAR 재구성에는 OS `libarchive`가 필요합니다.
기존 입력은 검증 후 유지하며, tracker·matcher 원본과 평가 GT를 준비합니다.
오프라인 검사는 `--offline`, 준비 범위는 `--purpose tracker|matcher|detection`으로 지정합니다.

Oxford 영상·등록 이미지는 직접 `data/detection/raw/town_centre.mp4`와
`data/detection/inputs/target.png`에 배치합니다. 원본·파생물은 로컬 전용이며
[데이터 출처·사용 조건](data/NOTICE.md)을 따릅니다.

## 실행

```bash
uv run motion-tracking --source data/tracker/inputs/11.mp4 --show-mask
uv run motion-tracking --source data/matcher/inputs/jogging.mp4 --target data/matcher/inputs/target.png
uv run motion-tracking --source data/tracker/inputs/11.mp4 --headless --output results/tracking.mp4 --csv results/tracks.csv
uv run motion-tracking --help
```

`--source 0`은 기본 웹캠입니다. `q` 종료, `p` 일시정지·재개, `s` 스냅샷 저장을 지원합니다.
타임라인 탐색은 MOG2와 추적 ID를 초기화합니다. 같은 추적 결과를 반복 확인하려면 저장한 MP4를 재생하세요.
화면 없는 환경에서는 `--headless`를 사용합니다. 출력 경로는 실행마다 다르게 지정하세요.

| 문서 | 내용 |
| --- | --- |
| [실행·평가 가이드](docs/recipes/tracker.md) | 설정, 영상별 관찰 구간, 실험 재현 명령 |
| [분석 보고서](docs/report.md) | 전경 분리 원인, 개선·회귀, 기존 측정, 다음 대안 |
| [결과 파일 안내](results/README.md) | 출력 구조와 덮어쓰기 동작 |
| [보존 근거 목록](docs/evidence/README.md) | 고정 CSV·이미지·환경 기록 |

## 개발 검증

```bash
make check
make test
make smoke
make build
make format
make run ARGS="--help"
```

`make smoke`는 임시 영상을 생성하는 headless 파이프라인 테스트만 실행합니다.
전체 테스트는 보존 데이터·연구 근거의 체크섬과 집계도 검증합니다.
단위·회귀 테스트와 실제 영상의 품질 평가는 별개입니다.
`make check`는 저장소 구조, Ruff 정적 검사와 포맷을 확인합니다.

## 패키지와 데이터 경로

`src/motion_tracking/`를 설치하며 `motion-tracking`, `motion-data-setup`,
`motion-data-verify` 명령을 등록합니다. 저장소 편집 설치에서는 다른 작업 디렉터리에서도
저장소의 `data/`와 `results/`를 사용합니다. wheel에는 영상·연구 근거를 포함하지 않습니다.
wheel 설치 후 데이터 준비·실험에는 원본 자료가 있는 작업 공간을
`MOTION_TRACKING_ROOT=/absolute/workspace`로 지정하세요. 지정하지 않으면 현재 디렉터리를 사용합니다.

실험은 `uv run --frozen python -m motion_tracking.experiments.<실험명>`으로 실행합니다.
기존 MOG2·SIFT·추적 설정, 조각 재구성의 기본 비활성화와 측정 프로토콜은 유지합니다.

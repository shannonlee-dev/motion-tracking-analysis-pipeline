# 구조 개편과 검증 기록

기준: 원격 `main`을 직접 조회한 `1607ce374a3cdb2da45948cb243e461a6f0f20c0`.
초기 앱부터 최근 데이터 정리까지 10개 커밋의 변경 이력, 전체 Python 파일, 문서·manifest를 검토했다.
이 문서는 구조 변경을 설명하며 실험 해석은 [분석 보고서](report.md)에 둔다.

## 기존 구조의 문제

- Tracker 01–19, Jogging 특징점 비교, Oxford 앱 시연의 역할이 디렉토리에서 드러나지 않았다.
- `command/1`–`19`의 반복 명령에 출력 경로가 섞였고 `results/submission`에는 평가 주석·실험 정의·세 종류 측정이 함께 있었다.
- 준비 스크립트가 특징점 실험과 보고서까지 생성했다. Jogging 스크립트의 저장소 루트 계산도 잘못되어 있었다.
- CAVIAR 다운로드는 기존 파일을 검증하지 않고 authoritative manifest의 해시를 다시 써서 손상을 정상으로 기록할 수 있었다.
- LASIESTA 준비는 정상 입력까지 다시 변환했다. 여러 문서의 과거 경로와 삭제된 안내 링크가 남아 있었다.
- Oxford 원본·등록 이미지가 NOTICE와 달리 Git에 추적되었고 명시적 제외 규칙이 없었다.
- 고정 0.45 배율의 상태 글자는 1080p에서 지나치게 작았다.

## 새 구조

```text
app.py
motion_tracking/
  cli.py                 # application CLI
  runner.py              # video pipeline, timeline, exports
  motion.py              # MOG2, contours/bbox
  tracker.py             # identity, missing state, trajectories
  matching.py            # full-frame ORB TargetMatcher
  display.py             # overlay styles, controls
  features.py            # common ratio matching
  config.py, constants.py, geometry.py
scripts/
  01_setup_data.py
  02_prepare_evaluation.py
  evaluate.py
datasets/                # source preparation and integrity
evaluation/              # independent measurement/export code
data/
  tracker/
    inputs/              # 01–19, preserved input bytes
    reference/           # manifests, licenses, events, GT, annotations
    raw/                 # ignored downloads and extracted archives
    generated/           # ignored state and reconstructed annotations
  matcher/
    inputs/              # jogging.mp4, target.png
    reference/           # licensed original JPG/GT, protocol, hashes
    raw/                 # ignored ZIP
    generated/           # ignored selected-frame derivatives and state
  detection/
    NOTICE.md
    reference/           # source hash and exact registration crop recipe
    raw/                 # ignored Oxford video
    inputs/              # ignored registered person image
    generated/           # ignored preparation/readiness manifests
results/
  tracker/
    baseline/{case_01…case_19,manual,submission,learning_rate}/
    runs/                # ignored new output
  matcher/
    baseline/{roi,application}/
    runs/
  detection/             # all ignored, local demo output
docs/
  report.md              # preserved analysis and limitations
  workflows.md           # copyable commands and prerequisites
  recipes/tracker.md     # case-specific historical settings/notes
  code-organization.md   # module responsibilities
  migration.md           # this record
tests/
```

`reference`는 실행 결과가 아니라 출처·정답·고정 조건이다. Jogging의 재배포 가능한 원본 JPG/GT는 작은 고정 재현 자료로 Git에 보존한다. `raw`는 다시 받을 수 있는 로컬 cache, `inputs`는 앱이 읽는 준비된 데이터, `generated`는 자동 준비 상태, `results`는 평가 출력이다. 사람의 분석 보고서를 자동 실행이 덮어쓰지 않는다.

## 이전 경로 → 새 경로

| 이전 | 새 위치 |
| --- | --- |
| `data/tracking_inputs` | `data/tracker/inputs` |
| `data/matching_inputs` | `data/matcher/inputs` |
| `data/final_inputs/final.mp4` | `data/detection/raw/town_centre.mp4` (로컬 보존, Git 제외) |
| `data/final_inputs/target.png` | `data/detection/inputs/target.png` (로컬 보존, Git 제외) |
| `data/reference/manifests` | `data/tracker/reference/manifests`; OTB는 `data/matcher/reference/sources.json` |
| `data/reference/lasiesta` | `data/tracker/reference/licenses` |
| `data/reference/matching_assets/Jogging-1/raw/Jogging` | `data/matcher/reference/Jogging` |
| `data/raw` | `data/tracker/raw`, `data/matcher/raw` |
| `results/1`–`19` | `results/tracker/baseline/case_01`–`case_19` |
| `results/submission/annotations`, `events.json`, `ground_truth.json` | `data/tracker/reference/` |
| `results/submission/feature*` | `results/matcher/baseline/application/` |
| `results/submission/learning_rate*` | `results/tracker/baseline/learning_rate/` |
| 나머지 `results/submission` | `results/tracker/baseline/submission/` |
| `results/jogging_matching` | `results/matcher/baseline/roi/` |
| `command/1`–`19` | `docs/workflows.md` 공통 실행 + `docs/recipes/tracker.md` 고유 설정/메모 |

## 통합·삭제한 코드

- `scripts/data/prepare_caviar.py`, `prepare_lasiesta.py`, `prepare_jogging_matching.py`의 사용자 진입점을 두 단계 스크립트로 통합했다. 다운로드·압축 해제·변환은 `datasets`로, ORB/SIFT 실험은 `evaluation/matcher.py`로 분리했다.
- `measure_submission`, `evaluate_submission`, `measure_background_gt`, `render_submission_review`는 `evaluate.py tracker --measure`로 조합한다. raw 주석 복원은 두 번째 준비 단계에서 재구성 가능한 경우 검증한다.
- 숫자별 명령 문서 19개의 반복 보일러플레이트, 중복 다운로드 함수, 이전 경로 상수 모듈, 사용되지 않는 `HOMOGRAPHY_MIN_MATCHES`, 분리 과정에서 남은 미사용 import를 제거했다.
- 기존 호환 import 모듈을 제거하고 구현 모듈(`motion.py`, `matching.py`)을 직접 사용한다. MOG2·Tracker·ORB 설정·연산 순서는 바꾸지 않았다.
- 영상·이미지·라이선스·유효한 기존 측정 파일은 삭제하지 않았다. 이전한 3,955개 파일을 검사했으며 누락 0, 바이너리 변경 0이다. 문서와 일부 provenance/CSV의 경로만 갱신했다.

## GUI 개선

`display.py`의 `OverlayStyle`로 최소 글꼴 크기, 해상도별 scale·두께·여백·줄 간격을 계산한다.
창·타임라인 콜백도 `VideoDisplay`로 분리해 영상 루프의 UI 코드를 줄였다.
FPS/Frame은 두 줄, ID와 TARGET DETECTED는 같은 배경 라벨 체계를 사용한다.
라벨은 프레임 안쪽으로 조정하고 폭이 좁으면 맞춘다. 원본 프레임은 변경하지 않는다.
타깃 판정·bbox 계산 알고리즘은 그대로다.

## 검증

- 변경 전 38개 테스트 통과. 이후 준비·고정 해시·ZIP 경로·외부 cwd·타깃 crop·누락 데이터 재구성·오버레이 회귀 테스트를 추가했다.
- Tracker 01–19: 각 40프레임, 총 760프레임 앱 smoke test; MP4·CSV 생성.
- Tracker 전체 주석 재현: 17개 평가 입력 × 4설정의 68개 trace와 사건 30개 집계를 재실행했다. 12·13은 기존 주석 프로토콜 대상이 아니다.
- 학습률: 525프레임 × 3설정, GT 픽셀 1,575행과 구간 요약 15개를 재실행했다.
- Matcher: ORB/SIFT × 5조건 및 앱 전체 프레임 비교 5조건을 재실행했다.
- 기존 baseline과 새 실행의 trace/측정 81개 파일이 일치한다. 과거 보고서의 수동 검토 한계는 그대로 유지한다.
- 준비 스크립트 정상 재실행, 실제 전체 디코딩, CLI 도움말, 외부 cwd 실행, Ruff 정적 검사, 문서 링크·이전 경로 검색, Oxford ignore 규칙을 확인한다.

최종 검증 결과:

- `python -m pytest -q`: **55 passed**. Ruff 검사·포맷 검사·Python compile 검사 통과.
- `01_setup_data.py`, `02_prepare_evaluation.py` 재실행: **3,749개 파일의 내용·수정 시각 불변**. raw archive 압축 해제 재실행도 확인했다.
- Oxford 앱 전체 실행: **7,502프레임, TARGET DETECTED 18프레임**. 최초 5768, 마지막 5829 (0-based). MP4 프레임 수와 CSV의 검출 프레임 수를 교차 확인했다.
- Oxford 5800번 프레임: 대응 27개, inlier 25개. 1080p와 저해상도 오버레이 이미지를 직접 확인했다.
- 빈 임시 디렉토리에 Oxford 로컬 원본을 가져오고 등록 이미지를 재생성해 두 파일의 고정 SHA-256 일치를 확인했다.
- 공식 Jogging 배포 페이지의 현재 다운로드로 ZIP을 실제 받아 기존 8,131,339바이트·SHA-256과 같음을 확인했다.
- 모든 원본의 무캐시 네트워크 다운로드를 다시 수행하지는 않았다. 특히 Oxford 토렌트의 현재 peer 가용성은 검증하지 않았다. 캐시 기반 준비·변환, 실제 로컬 원본 가져오기, 실패한 다운로드의 원자성·고정 해시 검사는 검증했다.
- README/문서의 로컬 링크와 실제 경로를 검사했다. migration 표 외에 폐기된 경로 참조는 없으며 Git에 노출되는 새 파일 중 raw/비공개/Oxford 파생물과 50MB 초과 파일은 없다.

## 남은 기술 부채와 운영 제한

- Oxford 파일이 과거 Git 이력에 남아 있다. 현재 파일은 로컬에 보존하고 새 경로는 제외하지만 과거 공개 이력을 없애려면 별도 이력 정리와 공유 저장소 조정이 필요하다.
- 원본 사이트·토렌트 가용성에 의존한다. Oxford 무캐시 자동 다운로드에는 `aria2c`, RAR 처리에는 OS libarchive가 필요하다. 로컬 원본 가져오기와 offline 경로를 제공한다.
- Tracker 04–11·14의 과거 인코더 설정은 불명확하다. 보존 입력은 고정 해시로 재현한다. 재구성 시 다른 인코더 결과는 별도 provenance에 기록하며 과거 수치와의 동일성을 주장하지 않는다.
- 타임라인·키 제어는 테스트의 OpenCV GUI 대체 함수를 통해 회귀 검증했다. 실제 데스크톱의 창 크기·폰트 체감은 별도 수동 확인 대상이다.
- 추적 실패 집계의 가림 제외 후보와 Jogging 각도·가림 정도는 기존 수동 근사이며 정밀 GT가 아니다.

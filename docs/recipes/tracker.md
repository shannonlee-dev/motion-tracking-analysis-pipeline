# 실행·평가 가이드

설치는 [README](../../README.md), 측정 결과·평가 정의는 [분석 보고서](../report.md)를 따른다.
아래 명령은 저장소 루트와 활성화된 Python 가상환경을 기준으로 한다. 프레임 번호는 0부터 시작한다.

## 앱 실행과 설정

```bash
python app.py --source data/tracker/inputs/11.mp4 --show-mask
python app.py --source data/tracker/inputs/11.mp4 --headless --output results/demo-11.mp4 --csv results/demo-11.csv
python app.py --source data/matcher/inputs/jogging.mp4 --target data/matcher/inputs/target.png
```

| 옵션 | 기본값 | 의미 |
| --- | ---: | --- |
| `--learning-rate` | 0.01 | MOG2 배경 학습률 |
| `--min-area` | 80 | 최소 contour 면적. bbox 사각형 면적이 아님 |
| `--open-kernel-size` | 3 | OPEN 타원 커널 크기 |
| `--kernel-size` | 3 | CLOSE 타원 커널 크기 |
| `--warmup-frames` | 25 | 시작 시 bbox를 내보내지 않는 프레임 수 |
| `--max-distance` | 50 | 중심점 대응 거리 상한, 픽셀 단위 |
| `--max-missing` | 15 | 연속 누락이 이 값을 초과하면 내부 트랙 삭제 |
| `--compose-fragments` | 0 | `1`이면 시간적 조각 재구성 후보 사용. 교차·가림 회귀로 기본 적용 보류 |

OPEN/CLOSE 크기를 함께 바꾸던 이전 실험은 **두 옵션을 같은 값**으로 지정한다.
커널은 양의 홀수다. 면적·거리의 기본값은 해상도나 화면 속 사람 크기에 자동 정규화되지 않는다.
MOG2 history=500, varThreshold=16, 그림자 검출을 사용하며 contour 면적은 화면의 50% 이하만 허용한다.

```bash
# 1·3·5 중 하나를 양쪽에 적용해 형태학 영향 비교
python app.py --source data/tracker/inputs/11.mp4 --show-mask --open-kernel-size 5 --kernel-size 5
# 조각 재구성 후보
python app.py --source data/tracker/inputs/19.mp4 --show-mask --compose-fragments 1
```

원인 비교는 한 설정씩 바꾼다. 17번 학습률은 0.001/0.01/0.1, 11번 거리는 50/80,
02번 missing은 15/30, 11번 면적은 20/80/200으로 비교할 수 있다.
면적 필터는 마스크를 바꾸지 않는다. missing 연장은 사라진 전경을 복원하지 않는다.

타임라인 탐색은 MOG2·Tracker를 초기화하므로 추적 비교는 **처음부터 처리한 출력 영상**으로 한다.
SIFT는 프레임별 매칭이어서 이 초기화와 독립적이다. 출력 MP4는 원본 FPS로 재생되며 별도 마스크 창은 저장하지 않는다.
CSV의 `time_s`는 원본 FPS 기준이고 현재 관측된 트랙만 기록한다.
처리 시작 후 지정한 출력은 덮어쓰므로 설정별 파일명을 구분한다. 첫 프레임 처리 실패 시 기존 CSV는 보존한다.

## 영상별 관찰 구간

01–03은 `.mpg`, 04–19는 `.mp4`이며 `data/tracker/inputs/`에 있다.
MPEG 컨테이너의 추정 프레임 수가 부정확할 수 있어 실제 디코딩 프레임을 기준으로 본다.
관찰 구간이 모두 정량 평가창인 것은 아니다. 정확한 평가창은 [events.json](../../data/tracker/reference/events.json)에 있다.

| 영상 | 관찰 구간 | 확인할 현상 |
| --- | --- | --- |
| 01 | f110–240 | 두 사람 접근·만남, 작은 검출 조각 |
| **02** | f30–85, f95–130 | 정상 이동, 짧은 정지·재연결. f103–124 공백 뒤 f125에서 missing 15는 새 ID 4, 30은 ID 1로 재연결한 관측 |
| 03 | f355–390, f625–660 | 매장 앞 정지, 뒤 사람과 약한 투영 겹침 |
| 04 | f65–100 | 매장 출입자와 대기자 합류 |
| 05 | f90–145 | 만남·방향 전환 |
| 06 | f90–147 | 접촉·분리, 기본 실행에서 ID 1→3 관측 |
| 07 | f45–155 | 몸싸움·긴 겹침, 평가 제외 구간 주의 |
| 08 | f50–145 | 큰 겹침과 누락. ID 변경 0이 성공을 뜻하지 않는 사례 |
| 09 | f65–192 | 접촉·추격·지속 가림 |
| 10 | f55–85 | 교차 가림, 작은 배경 사람 |
| **11** | f40–80, f25–149 | 출입 교차·신체 분리. 기본 실행 f73–77에서 ID 1→4, 4→3 관측 |
| 12 | 약 27–50초 | 문·외부광 변화. 사건별 GT 없음 |
| 13 | 약 60–75초·105–115초 | 휴대 조명·바닥 반사. 사건별 GT 없음 |
| 14 | f812·1853·2188 | 소등·점등·소등. 5 FPS, 수동 근사 bbox |
| 15 | f158–205 | 기둥 뒤 완전 가림 |
| 16 | f135–180 | 계단·벽 뒤 가림과 복귀 |
| **17** | f80–169, f177–256, f205–249, f270–379 | 접근·정지·블라인드 조명 변화·복귀 |
| **18** | f120–155 | f128 스위치 변화, 손 동작과 조명 변화가 혼합됨 |
| **19** | f159–273 | 문 앞 정지. 사람이 보여도 전경이 사라짐 |

정지 19번과 구조물 가림 15·16번을 구분한다. 기본값에서 19번 f180은 다리 조각만 남고 f220에는 박스가 없으며,
낮은 학습률은 사람과 배경 잔상을 함께 오래 남길 수 있다. 박스 수 감소나 검출 유지 자체가 정확도는 아니다.

SIFT 관찰 영상은 다음과 같다. 아래 값은 기존 시연 기록이며 현재 실행에서 다시 확인할 수 있다.

| 입력 | 관찰 구간·기록 | 해석 |
| --- | --- | --- |
| `data/matcher/inputs/jogging.mp4` | f32/64/67/139/299의 대응점 2/4/5/2/1, inlier 모두 0. 전체 영상 f0·1·18에서는 인식 | 방향·가림은 육안 근사. 이동 카메라여서 고정 배경 MOG2 대표 평가에 사용하지 않음 |
| `data/detection/raw/town_centre.mp4` | f5750·5780·5800·5820 인식, f5850은 대응 8/inlier 4로 실패 | f5800은 등록 원본 프레임. 이 성공은 일반화나 장기 Re-ID를 뜻하지 않음 |

Town Centre는 `--target data/detection/inputs/target.png`를 추가한다.
앞부분 300프레임만 실행하면 위 등록 대상은 나오지 않는다. 영상·파생물은 로컬 전용이다.

## 평가 재현

모든 측정은 실제 `runner.run()`을 호출한다. 실험별 파일 구조·덮어쓰기는 [결과 안내](../../results/README.md)를 따른다.

```bash
python -m experiments.tracker_metrics --output results/tracking --details
python -m experiments.learning_rate --output results/learning-rate --details
python -m experiments.feature_matching --output results/matching --details
```

학습률 픽셀 평가에는 데이터 준비 단계에서 받는 LASIESTA GT 525장이 필요하다.
현재 SIFT·추적 구현의 새 결과가 과거 ORB·추적 표와 같다고 가정하지 않는다.

조각 재구성 비교는 같은 기본 설정에서 활성화 여부만 바꾼다. 아래 출력 디렉터리는 새 경로여야 한다.

```bash
python -m experiments.fragmentation --config '{"compose_fragments":0}' --output results/fragmentation/baseline
python -m experiments.fragmentation --config '{"compose_fragments":1}' --output results/fragmentation/candidate
python -m experiments.fragmentation_compare \
  --baseline results/fragmentation/baseline --candidate results/fragmentation/candidate \
  --output results/fragmentation/comparison
python -m experiments.fragmentation_benchmark --output results/fragmentation/benchmark
# 개발 세트에서 기각한 OPEN 제거 실험
python -m experiments.fragmentation --videos 02 10 18 \
  --config '{"open_kernel_size":1,"compose_fragments":0}' --output results/fragmentation/open-ablation
```

GT 없는 고해상도 영상은 정량 정확도와 분리해 수동 검토한다.
아래는 이번 환경의 실제 원본 파일명이다. 원본 경로가 다르면 `--manual-source`를 바꾼다.

```bash
python -m experiments.fragmentation \
  --manual-source data/detection/raw/TownCentreXVID.mp4 --max-frames 300 --speed-repeats 1 \
  --config '{"compose_fragments":0}' --output results/detection/fragmentation-baseline
python -m experiments.fragmentation \
  --manual-source data/detection/raw/TownCentreXVID.mp4 --max-frames 300 --speed-repeats 1 \
  --config '{"compose_fragments":1}' --output results/detection/fragmentation-candidate
```

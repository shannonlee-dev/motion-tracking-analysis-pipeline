# 상수와 공통 코드

값은 의미와 사용 범위를 기준으로 관리한다. 같은 숫자라도 알고리즘 기본값과 데이터셋 규격처럼 변경 이유가 다르면 별도로 둔다.

| 위치 | 책임 |
| --- | --- |
| `motion_tracking/config.py` | 검증 가능한 실행 설정, 불변 `DEFAULT_CONFIG`, CLI에 노출할 필드 목록 |
| `motion_tracking/constants.py` | 공용 영상 코덱, FPS 대체값, 스냅샷 기본 경로, 시간 단위 |
| `motion_tracking/features.py` | ORB·SIFT 공용 특징점 수·매칭 기준과 ratio test·중복 대응 제거 |
| `motion_tracking/geometry.py` | 박스 교차 면적과 IoU 계산 |
| `motion_tracking/vision.py` | 전경 분리 임계값, 타깃 검출 판정 기준 |
| `motion_tracking/evaluation.py` | ID 확정·실패 판정 프레임 수, IoU·가림 평가 기준 |
| `motion_tracking/display.py` | 화면 스타일과 키보드 제어 상수 |
| `scripts/common.py` | 저장소 루트, 결과 루트, CSV 저장 |
| `scripts/constants.py` | 데이터셋 상대 경로·규격, 실험 seed·학습률·커널·거리 비교 값 |
| `scripts/data/synthetic.py` | 합성 장면의 크기·시간 구간·타깃 배치 |
| 각 데이터·평가 모듈 | 해당 모듈에만 필요한 레이블, 다운로드 제한, 검토 프레임 등 |

실행별 설정은 `Config(...)` 또는 `dataclasses.replace()`로 지정한다. 공통 모듈은 호출자를 import하지 않는다. `motion_tracking`은 `scripts`에 의존하지 않는다. 기존 `motion_tracking.evaluation.iou` import도 유지한다.

데이터셋 경로는 호출자의 `ROOT`에 결합하는 상대 경로다. 런타임 스냅샷 기본 경로는 기존처럼 현재 작업 디렉터리를 기준으로 한다. 평가 CSV 열 이름과 명령행 옵션은 유지한다.

검증: `.venv/bin/python -m pytest -q`

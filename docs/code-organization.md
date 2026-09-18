# 상수와 공통 코드

| 위치 | 책임 |
| --- | --- |
| `motion_tracking/config.py` | 실행 설정, 불변 DEFAULT_CONFIG, CLI 노출 필드와 검증 |
| `motion_tracking/constants.py` | 영상 코덱, FPS 대체값, 스냅샷 경로, 시간 단위 |
| `motion_tracking/features.py` | 특징점 수·매칭 기준, ratio test와 중복 대응 제거 |
| `motion_tracking/geometry.py` | 박스 좌표 타입 BBox |
| `motion_tracking/vision.py` | 전경 분리와 타깃 검출 판정 기준 |
| `motion_tracking/display.py` | 화면 스타일과 키보드 제어 |

실행별 설정은 Config 또는 dataclasses.replace로 지정한다.
스냅샷과 상대 출력 경로는 현재 작업 디렉터리를 기준으로 한다.

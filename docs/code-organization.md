# 코드 책임

| 모듈 | 책임 |
| --- | --- |
| `app.py`, `motion_tracking/cli.py` | 사용자 CLI, 설정·오류 해석 |
| `motion_tracking/runner.py` | 영상 입출력·프레임 루프·타임라인 reset·CSV/MP4 수명 |
| `motion_tracking/motion.py` | MOG2·마스크·contour/bbox |
| `motion_tracking/tracker.py` | 거리 매칭·ID·누락·궤적 |
| `motion_tracking/matching.py` | 앱의 전체 프레임 ORB·homography 판정 |
| `motion_tracking/features.py` | 공통 ratio test·descriptor 중복 제거 |
| `motion_tracking/display.py` | 해상도별 글꼴·라벨 배경·bbox·키 제어·창/타임라인 UI |
| `motion_tracking/config.py`, `constants.py` | 알고리즘 설정/검증, 영상 입출력 공통값 |
| `motion_tracking/vision.py` | 기존 Python import 호환용 재노출 |
| `datasets/paths.py` | 저장소 기준 경로, Tracker case 해석 |
| `datasets/storage.py`, `media.py` | 고정 해시 다운로드·안전한 압축 해제·원자적 파일 교체·BMP 변환 |
| `datasets/{tracker,jogging,detection}.py` | 목적별 원본·입력 준비 |
| `datasets/workflow.py` | 준비/검증 두 단계 조합 |
| `datasets/annotations.py` | 기존 raw GT에서 bbox를 재구성하는 검증 함수 |
| `evaluation/cli.py` | 세 평가 목적별 실행 조합 |
| `evaluation/{measurements,tracker,background,review,matcher}.py` | 측정·집계·시각 근거 생성 |

앱은 `datasets`나 `evaluation`을 import하지 않는다. 실험이 앱 알고리즘을 가져다 쓴다.
MOG2·Tracker·ORB 임곗값과 매칭 순서는 기존과 동일하다. 데이터를 준비하는 것만으로 측정을 재실행하거나 보존 결과를 덮어쓰지 않는다.

# 실험 결과 파일

`results/`는 새 실행 결과를 저장하며 Git에서 제외한다.
재현 명령은 [실행·평가 가이드](../docs/recipes/tracker.md), 해석은 [분석 보고서](../docs/report.md)에 있다.

| 실험 | 주요 산출물 | 재실행 동작 |
| --- | --- | --- |
| `tracker_metrics`, `learning_rate`, `feature_matching` | `summary.csv`, `comparison.jpg`, `metadata.json`; `--details` 사용 시 상세 파일 | 성공 시 해당 폴더 교체. 실패 시 기존 결과 유지. 기본 모드 재실행은 이전 `details/`도 제거 |
| `fragmentation` | `summary.csv`, `events.csv`, 영상별 `*_metrics.csv`, `*_stages.csv`, `*_tracks.json`, `*_stages.jpg`, `metadata.json` | 새 출력 폴더 필요 |
| `fragmentation` · GT 없는 입력 | `manual.csv`, 영상별 단계 화면·진단·trace, `metadata.json` | 정량 정확도 미집계, 수동 검토용 |
| `fragmentation_compare` | `comparison.csv`, 영상별 비교 화면, `selection.json` | 저장된 전후 trace 비교, 새 출력 폴더 필요 |
| `fragmentation_benchmark` | `timings.csv`, `metadata.json` | 앱 AB/BA 반복 속도 측정, 새 출력 폴더 필요 |
| 앱 `--output`, `--csv` | 지정한 MP4·CSV | 처리 시작 후 지정 파일 덮어쓰기 |

`metadata.json`은 실행 설정·환경·입력 및 코드 해시를 기록한다.
조각 평가 trace의 `components`는 검출 조각, `boxes`는 구성 객체, `tracks`는 실제 활성 ID다.
축소 비교 화면은 탐색용이며 정확한 위치·ID는 trace와 원영상을 함께 확인한다.

실행별 출력 경로를 구분하고 [고정 근거](../docs/evidence/README.md)에 직접 덮어쓰지 않는다.
Oxford 원본·결과는 로컬 전용이다. 과거 `detection/summary.json`은 앱의 영상 저장 명령으로 갱신되지 않는다.

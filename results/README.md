# 결과 자료

| 위치 | 역할 |
| --- | --- |
| `tracker/baseline/case_01`–`case_19` | 이전 영상·CSV·캡처 보존 |
| `tracker/baseline/submission` | 기존 네 설정 trace·사건 집계·검토 근거 |
| `tracker/baseline/learning_rate` | 17번 영상의 세 학습률·GT 픽셀 측정 |
| `matcher/baseline/roi` | Jogging ORB/SIFT ROI 실험 및 자동 생성 보고서 |
| `matcher/baseline/application` | Jogging 전체 프레임 앱 ORB 비교 |
| `<목적>/runs` | 새 실행의 자동 생성 결과; Git 제외 |
| `detection` | Oxford 로컬 전용 결과; 전체 Git 제외 |

사람이 작성한 분석과 복사할 명령은 [docs/report.md](../docs/report.md)에 있다.
주석·사건 정의는 `data/tracker/reference/`에 둔다. `baseline`은 이전 실험의 증거이며 새 실행 결과가 아니다. 추적 집계의 수동 검토 한계는 보고서에 유지했다.

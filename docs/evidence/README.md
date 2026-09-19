# 보고서의 고정 측정 근거

이 폴더는 [분석 보고서](../report.md)의 과거 측정값과 검토 근거를 보존한다.
기존 `results/*/baseline/`에서 내용 변경 없이 옮겼으며, 실험 재실행으로 갱신하지 않는다.
최신 실행 결과는 [results](../../results/README.md)에서 확인한다.

| 위치 | 내용 |
| --- | --- |
| [tracking](tracking/tracking_summary.csv) | 네 추적 설정의 집계, 사건별 기록, trace, 검토 이미지 |
| [learning-rate](learning-rate/learning_rate_summary.csv) | 세 학습률의 구간 집계, 픽셀 측정, 관찰 이미지 |
| [matching](matching/features.csv) | 앱 전체 프레임 ORB 측정 |
| [matching-roi](matching-roi/metrics.csv) | 별도 ORB/SIFT ROI 실험 |

환경 및 입력 해시는 [기존 환경 기록](tracking/environment.json)을 따른다.

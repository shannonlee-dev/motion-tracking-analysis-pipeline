# 고정 측정 근거

실험 당시 CSV·이미지·환경 기록을 보존한다. 새 실행은 `results/`에 저장한다.
해석·평가 정의는 [분석 보고서](../report.md), 재현 명령은 [실행·평가 가이드](../recipes/tracker.md)에 있다.

| 위치 | 내용·주의점 |
| --- | --- |
| [fragmentation](fragmentation/comparison/comparison.csv) | 2026-09-21 신체 조각 비교. `baseline/`, `candidate/`, `open-ablation/`, `comparison/`, `benchmark/`와 기본 적용 보류 기록 `promotion.json` |
| [tracking](tracking/tracking_summary.csv) | 기존 네 추적 설정, 사건별 기록·trace·화면. IoU 0.1 기준 잠정 결과 |
| [learning-rate](learning-rate/learning_rate_summary.csv) | 세 학습률의 LASIESTA 픽셀 측정·원시 라벨 비율 |
| [morphology](morphology/comparison.json) | OPEN/CLOSE 커널 크기 비교 |
| [matching](matching/features.csv) | 과거 전체 프레임 ORB 측정. 현재 SIFT 결과가 아님 |
| [matching-roi](matching-roi/metrics.csv) | 위치를 아는 ROI의 ORB/SIFT 비교 |
| [matching-preprocessing](matching-preprocessing/metrics.csv) | 회색조·확대 전처리 비교. 전체 프레임 인식률이 아님 |

기존 추적 표의 환경은 [tracking/environment.json](tracking/environment.json)을 따른다.
조각 평가의 실제 설정·해시는 각 실행의 `metadata.json`, 최종 기본값과 소스 해시는
[fragmentation/promotion.json](fragmentation/promotion.json)에 있다. 과거 소스 해시는 당시 문서 참조를 포함하므로 문서 통합 후의 해시와 다를 수 있다.

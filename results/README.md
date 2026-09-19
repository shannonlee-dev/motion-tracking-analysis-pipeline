# 최신 실험 결과

각 폴더에서 요약 CSV와 비교 이미지를 먼저 확인한다. 실행 환경·입력 해시·설정은 `metadata.json`에 기록한다.

| 실험 | 요약 | 비교 이미지 | 재실행 |
| --- | --- | --- | --- |
| 추적 | [tracking/summary.csv](tracking/summary.csv) | [comparison.jpg](tracking/comparison.jpg) | `python -m experiments.tracker_metrics` |
| 학습률 | [learning-rate/summary.csv](learning-rate/summary.csv) | [comparison.jpg](learning-rate/comparison.jpg) | `python -m experiments.learning_rate` |
| 매칭 | [matching/summary.csv](matching/summary.csv), [ROI 비교](matching/roi-summary.csv) | [comparison.jpg](matching/comparison.jpg) | `python -m experiments.feature_matching` |
| 대상 검출 | [detection/summary.json](detection/summary.json) | [video.mp4](detection/video.mp4) | 아래 앱 명령 |

```bash
python app.py --source data/detection/raw/town_centre.mp4 --target data/detection/inputs/target.png --headless --output results/detection/video.mp4
```

대상 검출은 앱의 영상 저장 기능을 사용한다. `summary.json`은 기존 실행의 집계이며 위 명령으로 갱신되지 않는다.
Oxford 영상과 결과는 로컬 전용이다.

- 기본 실험 결과는 3개 파일이며 매칭만 앱·ROI 요약을 분리해 4개다.
- 세 실험 명령은 `--details`를 지정할 때만 상세 CSV·JSON·개별 이미지를 `details/` 한 단계에 저장한다. 비교 이미지는 탐색용 축소본이며, 정밀한 검토에는 상세 이미지를 사용한다. 공통 실행 정보와 요약은 상위 폴더에만 둔다.
- 재실행에 성공하면 해당 실험 폴더를 교체한다. 기본 모드로 재실행하면 이전 `details/`도 제거한다. 실패하면 기존 결과를 유지한다.
- 실행을 별도로 보존하려면 `--output /tmp/matching-check`처럼 다른 경로를 지정한다.
- 기본 실행의 중간 데이터와 이미지는 메모리로 전달한다. 추적 기록은 영상 한 편씩 처리하고, 비교용 이미지는 축소해서 모은다. 중간 파일을 저장했다 다시 읽지 않는다.
- 결과 교체용 임시 폴더에는 최종 파일만 작성한다(`--details` 사용 시 상세 파일 포함). 성공 후 실험 폴더로 옮기며, 최신 산출물은 Git에서 제외한다.

과거 보고서 수치와 검토 근거는 [docs/evidence](../docs/evidence/README.md)에 고정 보존한다.
해석과 측정 한계는 [분석 보고서](../docs/report.md)를 참고한다.

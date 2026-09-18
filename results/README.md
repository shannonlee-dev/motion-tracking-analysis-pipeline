# 제출 보고서와 측정 근거

현재 재실행 결과는 [submission/](submission/)에, 설명은 [docs/report.md](../docs/report.md)에 있다.
특징점·17번 학습률 실험은 완료했으며 추적 표는 실제 가림·객체 대응 검토가 남은 **잠정 결과**다.

- `submission/features.csv`: 앱 `TargetMatcher`의 전체 프레임 ORB 결과.
- `submission/event_log.csv`: 사건 30개의 6열 원본 로그와 집계 구간.
- `submission/tracking_summary.csv`: 설정별·조건별 잠정 추적 집계.
- `submission/frame_assignments.csv`, `counted_runs.json`: 프레임 대응 및 5/10프레임 판정 근거.
- `submission/learning_rate_summary.csv`: 17번 영상의 세 학습률 GT 픽셀 비교.
- `submission/review/`: 사건별 관찰 이미지. `EXCL?`은 가림 제외 후보다.
- `jogging_matching/`: 분모를 수정한 기존 ROI 참고 실험. 제출 특징점 주 결과가 아니다.
- `1/`–`19/`: 기존 앱 결과 영상·CSV. 새 실험의 최종 집계 근거로 사용하지 않았다.

재현 명령, 설정, 현재 미충족 항목은 보고서에 명시했다.

## 이전 경로 안내 (현재 폴더 구성과 다름)


현재 입력 경로에 맞춰 결과를 구분한다.

| 입력 | 결과 | 내용 |
| --- | --- | --- |
| `data/tracking_inputs/caviar/*.mpg` | `caviar/` | CAVIAR overlap·single·stationary 결과 |
| `data/tracking_inputs/lasiesta/<시퀀스명>/` | `lasiesta/` | LASIESTA 시퀀스별 기존 분석 결과 |

```text
results/
├── caviar/
│   ├── videos/      # CAVIAR 추적 결과 영상
│   ├── captures/    # 관찰 캡처
│   ├── traces/      # 프레임별 로그
│   └── metrics/     # 추적·객체별 집계와 영상 정보
└── lasiesta/
    ├── captures/    # 조명 변화·정지 관찰 캡처
    ├── traces/      # 프레임별 검출·추적 로그
    └── metrics/     # 조명·추적 집계
```

새 영상·로그는 `--output`, `--csv`로 해당 입력의 결과 폴더에 저장한다.
예: `--output results/caviar/videos/single_1_overlap_1.mp4 --csv results/caviar/traces/single_1_overlap_1.csv`.
스냅샷은 s 키로 저장하며, 기본 경로는 `results/snapshots/`이다. `--snapshot-dir`로 입력에 맞는 `captures/`를 지정할 수 있다. 이 폴더들은 저장할 때 생성된다.

영상·캡처를 관찰하고 영상명·프레임 범위·메모를 `docs/report.md`에 기록한다.
출처와 이용 조건은 `data/NOTICE.md`를 확인한다.

LASIESTA의 장면별 폴더명과 기존 결과의 원본 ID 대응은 `data/reference/lasiesta/NOTICE.md`에 기록되어 있다.

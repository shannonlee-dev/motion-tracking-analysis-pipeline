# 입력별 분석 결과

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

LASIESTA의 장면별 폴더명과 기존 결과의 원본 ID 대응은 `data/lasiesta/NOTICE.md`에 기록되어 있다.

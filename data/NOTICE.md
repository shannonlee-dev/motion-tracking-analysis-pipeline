# 데이터 출처 및 이용 조건

실제 영상과 XML은 에든버러대학교가 제공하는
[CAVIAR Test Case Scenarios](https://homepages.inf.ed.ac.uk/rbf/CAVIARDATA1/)에서 확보했습니다.
공식 페이지는 공개 다운로드, Creative Commons BY-SA 이용 조건 및 결과 발표 시
**EC Funded CAVIAR project/IST 2001 37540** 출처 표기를 안내합니다.
페이지에 라이선스 버전 번호가 명시되어 있지 않으므로 임의의 버전을 붙이지 않았습니다.

| 로컬 파일 | 원본 시나리오 | 사용 목적 |
| --- | --- | --- |
| `raw/meeting.mpg` | Meet_WalkSplit | 두 사람 만남·겹침·분리, 필수 약 25초 영상 |
| `raw/walking.mpg` | Walk1 | 단일 대상 구간 관찰; 전체 영상에는 여러 사람 등장 |
| `raw/stopping.mpg` | OneStopNoEnter1cor | 보행 후 정지·재이동 |

다운로드한 파일별 주소·바이트 수·SHA-256은 `sources.json`에 있습니다.
다운로드·평가 범위는 `meeting`·`walking`·`stopping` 3개입니다.
`raw/`의 MPEG 영상 3개와 정답 XML 3개는 원본 내용의 변경 없이 이 저장소에 재배포합니다.
해당 데이터는 배포처가 명시한 Creative Commons BY-SA 조건을 유지합니다.
이를 바탕으로 만든 CAVIAR 오버레이 영상과
`results/current/captures/caviar_*.jpg`도 원본의 출처와 BY-SA 조건을 유지합니다.
미디어와 다운로드 주소는 실행 파일이 아닙니다.

`target.png` 및 `clips/single_*`, `crossing_*`, `stopping_*`, `lighting_*`, `target_demo.mp4`는
이 프로젝트의 `scripts/eval/run.py`가 생성한 통제 실험 자료입니다.
실제 사람의 촬영이나 독립적인 현장 시험으로 해석하면 안 됩니다.

추가 자료는 [LASIESTA](lasiesta/NOTICE.md), [ALOI](aloi/NOTICE.md)의
개별 이용 조건과 재현 방법을 따릅니다.

## 공개 범위

소스, 직접 작성한 문서, 합성 영상, 측정 CSV, 추적 로그와 재배포가 허용된
데이터·분석 영상·캡처를 공개 대상으로 둔다. 재생성 가능 여부나 확장자만으로
`data/` 또는 `results/`를 일괄 제외하지 않는다.
가상환경·캐시·로컬 비밀 설정과 아래 허가 미확인 자료만 `.gitignore`로 제외한다.

## LASIESTA

[공식 데이터 안내](https://gti.ssr.upm.es/data/lasiesta_database)의 검색 색인에서
**CC BY-SA 4.0** 및 재배포 허용 문구를 확인했다(2026-09-13).
검증 불가: 공식 페이지 직접 접속은 시간 초과였으며, 이용 조건은 검색 색인 본문으로 확인했다.
[라이선스 조건](https://creativecommons.org/licenses/by-sa/4.0/)에 따라
출처·변경 내용을 표시하고 가공물에도 같은 라이선스를 유지한다.

출처: C. Cuevas, E. M. Yáñez, N. García,
“Labeled dataset for integral evaluation of moving object detection algorithms: LASIESTA”,
Computer Vision and Image Understanding, 152, 103–117, 2016.
DOI: 10.1016/j.cviu.2016.08.005.

`data/lasiesta/*.rar`는 내려받은 압축 자료,
`data/lasiesta/extracted/`는 추출한 프레임·정답·XML이다.
LASIESTA에서 만든 평가 영상과 `results/current/captures/I_*.jpg`는
프레임 추출·합성 또는 분석 표시가 추가된 가공물로 CC BY-SA 4.0으로 제공한다.
대상 시퀀스는 I_IL_01, I_IL_02, I_OC_01, I_OC_02, I_CA_01이다.

## 재배포 허가 미확인 자료

- ALOI: 기존 보고서의 확인 결과상 명시적인 재배포 허가가 없다.
  이번 공식 홈페이지 조회에서도 이용 조건 본문을 확보하지 못했다.
  `data/download/aloi_*`와 `data/aloi/raw/`의 원본·마스크·가공 이미지는
  로컬에만 보관한다. 출처 안내, 다운로드 코드와 수치 평가 결과는 제외하지 않는다.
- `docs/private/mission.md`, `docs/private/rubric.md`: 제공받은 과제·평가 기준
  원문으로, 재배포 허가가 확인될 때까지 로컬에 보관한다.

허가가 확인되면 해당 경로의 제외 규칙을 제거하고 출처와 조건을 여기에 기록한다.
교육 목적이라는 이유만으로 외부 자료의 재배포 권한이 있다고 가정하지 않는다.

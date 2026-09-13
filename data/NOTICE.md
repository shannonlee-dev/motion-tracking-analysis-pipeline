# 데이터 출처 및 이용 조건

에든버러대학교의 영상·XML을 [CAVIAR Test Case Scenarios](https://homepages.inf.ed.ac.uk/rbf/CAVIARDATA1/)에서 확보했습니다.
Creative Commons BY-SA(버전 미명시) 조건과 **EC Funded CAVIAR project/IST 2001 37540** 출처 표기를 유지합니다.

| 로컬 파일 | 원본 시나리오 | 사용 목적 |
| --- | --- | --- |
| `raw/meeting.mpg` | Meet_WalkSplit | 두 사람 만남·겹침·분리, 필수 약 25초 영상 |
| `raw/walking.mpg` | Walk1 | 단일 대상 구간 관찰; 전체 영상에는 여러 사람 등장 |
| `raw/stopping.mpg` | OneStopNoEnter1cor | 보행 후 정지·재이동 |

파일별 주소·크기·SHA-256은 `sources.json`에 있습니다. 위 3개 MPEG·XML은 원본 그대로 재배포하며,
CAVIAR 오버레이 영상·`results/current/captures/caviar_*.jpg`에도 출처와 BY-SA 조건을 유지합니다.

`target.png`, `clips/single_*`·`crossing_*`·`stopping_*`·`lighting_*`·`target_demo.mp4`는
`scripts/eval/run.py`가 생성한 통제 자료로, 실제 촬영·독립 현장 시험이 아닙니다.
추가 자료의 출처·재현 방법은 [LASIESTA](lasiesta/NOTICE.md)와 [ALOI](aloi/NOTICE.md)를 참조합니다.

## 공개 범위

소스·작성 문서·합성 영상·측정 CSV·로그와 재배포 허용 데이터·가공물을 공개합니다.
`data/`·`results/`를 일괄 제외하지 않으며 가상환경·캐시·비밀 설정·재생성 가능한 LASIESTA 해제본·아래 허가 미확인 자료를 `.gitignore`로 제외합니다.

## LASIESTA

[공식 데이터 안내](https://gti.ssr.upm.es/data/lasiesta_database)의 검색 색인에서
**CC BY-SA 4.0** 및 재배포 허용 문구를 확인했다(2026-09-13).
검증 불가: 공식 페이지 직접 접속은 시간 초과였으며, 이용 조건은 검색 색인 본문으로 확인했다.
[라이선스 조건](https://creativecommons.org/licenses/by-sa/4.0/)에 따라
출처·변경 내용을 표시하고 가공물에도 같은 라이선스를 유지한다.

I_IL_01·I_IL_02·I_OC_01·I_OC_02·I_CA_01의 원본 RAR과
평가 영상·`results/current/captures/I_*.jpg`를 포함합니다. 가공물은 프레임 합성·분석 표시를 추가했으며 CC BY-SA 4.0을 유지합니다.
추출 프레임·GT·XML은 원본과 중복되므로 Git에서 제외합니다.
`python -m scripts.data.prepare`로 `data/lasiesta/extracted/`에 재생성하며 로컬 평가에 사용합니다.
논문 출처와 원본·가공물 구분은 [LASIESTA 안내](lasiesta/NOTICE.md)에 있습니다.

## 재배포 허가 미확인 자료

- ALOI: 기존 보고서의 확인 결과상 명시적인 재배포 허가가 없다.
  이번 공식 홈페이지 조회에서도 이용 조건 본문을 확보하지 못했다.
  `data/download/aloi_*`와 `data/aloi/raw/`의 원본·마스크·가공 이미지는
  로컬에만 보관한다. 출처 안내, 다운로드 코드와 수치 평가 결과는 제외하지 않는다.
- `docs/private/mission.md`, `docs/private/rubric.md`: 제공받은 과제·평가 기준
  원문으로, 재배포 허가가 확인될 때까지 로컬에 보관한다.

허가가 확인되면 해당 경로의 제외 규칙을 제거하고 출처와 조건을 여기에 기록한다.
교육 목적이라는 이유만으로 외부 자료의 재배포 권한이 있다고 가정하지 않는다.

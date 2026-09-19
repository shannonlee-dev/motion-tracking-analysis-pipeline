# 데이터 출처 및 이용 조건

에든버러대학교의 영상을 [CAVIAR Test Case Scenarios](https://homepages.inf.ed.ac.uk/rbf/CAVIARDATA1/)에서 확보했습니다.
Creative Commons BY-SA(버전 미명시) 조건과 **EC Funded CAVIAR project/IST 2001 37540** 출처 표기를 유지합니다.

| 로컬 파일 | 원본 시나리오 | 사용 목적 |
| --- | --- | --- |
| `tracker/inputs/01.mpg` | Meet_WalkSplit | 두 사람 만남·겹침·분리, 필수 약 25초 영상 |
| `tracker/inputs/02.mpg` | Walk1 | 단일 대상 구간 관찰; 전체 영상에는 여러 사람 등장 |
| `tracker/inputs/03.mpg` | OneStopNoEnter1cor | 보행 후 정지·재이동 |

파일별 주소·크기·SHA-256은 `data/tracker/reference/manifests/caviar_sources.json`에 있습니다. 위 3개 MPEG 영상은 원본 그대로 재배포하며,
CAVIAR 영상으로 만든 오버레이·캡처에도 출처와 BY-SA 조건을 유지합니다.

추가 자료의 출처는 [LASIESTA](tracker/reference/licenses/NOTICE.md)를 참조합니다.

OTB2015 Jogging-1의 원본·출처·CC BY 4.0 표기와 가공 내용은 [OTB2015 안내](matcher/NOTICE.md)를 참조합니다.

Oxford Town Centre 영상과 여기서 추출한 등록 이미지는 [Oxford Town Centre 안내](detection/NOTICE.md)를 참조합니다.
배포 페이지에 라이선스가 명시되어 있지 않으므로 재배포 허가가 확인될 때까지 Git에서 제외합니다.

## 공개 범위

소스·작성 문서·관찰용 영상과 재배포 허용 데이터·가공물을 공개합니다.
`data/`·`results/`를 일괄 제외하지 않으며 가상환경·캐시·비밀 설정·`data/tracker/raw/`의 재생성 가능한 원본·아래 허가 미확인 자료를 `.gitignore`로 제외합니다.

## LASIESTA

[공식 데이터 안내](https://gti.ssr.upm.es/data/lasiesta_database)의 검색 색인에서
**CC BY-SA 4.0** 및 재배포 허용 문구를 확인했다(2026-09-13).
검증 불가: 공식 페이지 직접 접속은 시간 초과였으며, 이용 조건은 검색 색인 본문으로 확인했다.
[라이선스 조건](https://creativecommons.org/licenses/by-sa/4.0/)에 따라
출처·변경 내용을 표시하고 가공물에도 같은 라이선스를 유지한다.

I_IL_01·I_IL_02·I_OC_01·I_OC_02·I_CA_01의 원본 RAR과 추출 BMP 프레임·GT·XML은 재생성할 수 있으므로 Git에서 제외합니다.
`python scripts/01_setup_data.py --purpose tracker --raw`로 `data/tracker/raw/lasiesta/`에 원본 ID를 유지해 풀고, BMP 프레임을
`data/tracker/inputs/15.mp4`부터 `19.mp4`까지 변환합니다. OS libarchive와 Python libarchive-c가 필요합니다.
논문 출처와 원본·가공물 구분은 [LASIESTA 안내](tracker/reference/licenses/NOTICE.md)에 있습니다.

## 재배포 허가 미확인 자료

- `docs/private/mission.md`, `docs/private/rubric.md`: 제공받은 과제·평가 기준
  원문으로, 재배포 허가가 확인될 때까지 로컬에 보관한다.
- `data/detection/raw/town_centre.mp4`: Oxford Town Centre Dataset 영상.
  Academic Torrents 배포 페이지에 라이선스가 명시되어 있지 않아 로컬에서만 사용한다.
- `data/detection/inputs/target.png`: 위 영상 5800번 프레임에서 추출한 파생 이미지.
  원본과 같은 재배포 제한을 적용한다.

허가가 확인되면 해당 경로의 제외 규칙을 제거하고 출처와 조건을 여기에 기록한다.
교육 목적이라는 이유만으로 외부 자료의 재배포 권한이 있다고 가정하지 않는다.

## 추가 겹침 장면

겹침 장면 8개 (`data/tracker/reference/manifests/overlap_sources.json`)는 같은 CAVIAR 출처와 Creative Commons BY-SA(버전 미명시) 조건을 따른다. **EC Funded CAVIAR project/IST 2001 37540**. 원본에서 구간을 발췌해 H.264 MP4로 재인코딩했으며 미리보기에는 시점 글자를 추가했다. 출처·해시·발췌 범위는 `data/tracker/reference/manifests/overlap_sources.json`에 기록했다.

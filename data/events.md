## 표. 추적 성능 측정 결과

19개 입력을 처음부터 끝까지 프레임 단위로 확인했다. 파일 번호는 [매니페스트](manifests/)의 `local_file` 값과 같다.

| 입력 파일 | 장면·출처 | 단일 이동 | 두 객체 겹침 | 일시 정지 | 조명 변화 | 가림 |
|---|---|---:|---:|---:|---:|---:|
| `01.mpg` | Meet_WalkSplit | 1 | 1 | 0 | 0 | 0 |
| `02.mpg` | Walk1 | 2 | 0 | 1 | 0 | 0 |
| `03.mpg` | OneStopNoEnter1cor | 2 | 0 | 1 | 0 | 0 |
| `04.mp4` | OneShopOneWait1cor | — | 1 | — | — | 0 |
| `05.mp4` | Meet_WalkTogether2 | — | 1 | — | — | 0 |
| `06.mp4` | Fight_RunAway1 | — | 1 | — | — | 0 |
| `07.mp4` | Fight_RunAway2 | — | 1 | — | — | 0 |
| `08.mp4` | Fight_OneManDown | — | 1 | — | — | 0 |
| `09.mp4` | Fight_Chase | — | 1 | — | — | 0 |
| `10.mp4` | EnterExitCrossingPaths1cor | — | 1 | — | — | 0 |
| `11.mp4` | EnterExitCrossingPaths2cor | — | 1 | — | — | 0 |
| `12.mp4` | CSIRO human_door | 1 | 0 | 0 | 1 | 0 |
| `13.mp4` | CSIRO human_light | 2 | 0 | 0 | 2 | 0 |
| `14.mp4` | Wallflower LightSwitch | 2 | 0 | 1 | 3 | 0 |
| `15.mp4` | LaSIESTA I_OC_01, 기둥 | 1 | 0 | 0 | 0 | 1 |
| `16.mp4` | LaSIESTA I_OC_02, 계단·벽 | 1 | 0 | 0 | 0 | 1 |
| `17.mp4` | LaSIESTA I_IL_02, 블라인드 | 1 | 0 | 1 | 1 | 0 |
| `18.mp4` | LaSIESTA I_IL_01, 스위치 | 1 | 0 | 1 | 1 | 0 |
| `19.mp4` | LaSIESTA I_CA_01, 빨간 문 | 1 | 0 | 1 | 0 | 0 |
| **합계 / 필요** |  | **15 / 10** | **9 / 10** | **6 / 5** | **8 / 5** | **2** |

`—`는 해당 영상에서 그 조건을 측정하지 않았다는 뜻이며 0은 프레임을 확인했지만 해당 사건이 없었다는 뜻이다. `03.mpg`는 한 사람의 이동·정지·재이동 장면으로, 기존 표의 겹침 1회 표기를 수정했다. `10.mp4`와 `11.mp4`는 두 사람이 교차하며 부분적으로 가려지지만, 이 표에서는 CAVIAR의 선정 기준에 따라 두 객체 겹침으로 집계했다. `15.mp4`와 `16.mp4`의 가림은 겹침과 구분되는 LaSIESTA 가림 장면으로 별도 집계했다. 이 표는 평가용 장면 수이며 추적 성공 횟수가 아니다.

## 표. 추적 성능 측정 결과

| 파일·폴더 | 단일 이동 | 두 객체 겹침 | 일시 정지 | 조명 변화 |
|---|---:|---:|---:|---:|
| `single_2_stationary_1.mpg` | 2 | 0 | 1 | 0 |
| `single_1_overlap_1.mpg` | 1 | 1 | 0 | 0 |
| `single_2_overlap_1_stationary_1.mpg` | 2 | 1 | 1 | 0 |
| `single_1_stationary_1_red_door` | 1 | 0 | 1 | 0 |
| `single_1_stationary_1_lighting_1_switch` | 1 | 0 | 1 | 1 |
| `single_1_stationary_1_lighting_1_blinds` | 1 | 0 | 1 | 1 |
| `single_1_pillar_occlusion` | 1 | 0 | 0 | 0 |
| `single_1_stairwell_occlusion` | 1 | 0 | 0 | 0 |
| `single_1_lighting_1_door.mp4` | 1 | 0 | 0 | 1 |
| `single_2_lighting_2_portable_light.mp4` | 2 | 0 | 0 | 2 |
| `single_2_stationary_1_lighting_3_switch.mp4` | 2 | 0 | 1 | 3 |
| `overlap_1_OneShopOneWait1cor.mp4` | — | 1 | — | — |
| `overlap_1_Meet_WalkTogether2.mp4` | — | 1 | — | — |
| `overlap_1_Fight_RunAway1.mp4` | — | 1 | — | — |
| `overlap_1_Fight_RunAway2.mp4` | — | 1 | — | — |
| `overlap_1_Fight_OneManDown.mp4` | — | 1 | — | — |
| `overlap_1_Fight_Chase.mp4` | — | 1 | — | — |
| `overlap_1_EnterExitCrossingPaths1cor.mp4` | — | 1 | — | — |
| `overlap_1_EnterExitCrossingPaths2cor.mp4` | — | 1 | — | — |
| **합계 / 필요** | **15 / 10** | **10 / 10** | **6 / 5** | **8 / 5** |

추가 8개는 [겹침 장면 목록](overlap-scenes.md)의 서로 다른 원본에서 1개씩 선정했다. `—`는 이번 추가분에서 해당 항목을 미집계했다는 뜻이며, 나머지 항목의 합계는 기존 집계를 유지했다. 이 표는 평가용 장면 수이며 추적 성공 횟수가 아니다.

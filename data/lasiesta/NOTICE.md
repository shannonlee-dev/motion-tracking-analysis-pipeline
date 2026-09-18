# LASIESTA 및 추가 조명 영상의 원본·이용 조건

제공자: Grupo de Tratamiento de Imágenes, Universidad Politécnica de Madrid.
공식 배포: https://www.gti.ssr.upm.es/data/LASIESTA
이용 조건: Creative Commons Attribution-ShareAlike 4.0 International.
https://creativecommons.org/licenses/by-sa/4.0/

참고 논문: Carlos Cuevas, Eva M. Yáñez, Narciso García,
“Labeled dataset for integral evaluation of moving object detection algorithms: LASIESTA”,
Computer Vision and Image Understanding, 2016. DOI: 10.1016/j.cviu.2016.08.005.

I_IL_01.rar, I_IL_02.rar, I_OC_01.rar, I_OC_02.rar, I_CA_01.rar을 준비 스크립트에서 사용한다.
파일별 공식 URL·바이트 수·SHA-256은 `data/manifests/lasiesta_sources.json`에 있다.
`python -m scripts.data.prepare_lasiesta`로 원본 RAR과 프레임·GT·XML을 `data/raw/lasiesta/`에 원본 ID 그대로 저장한다.
OS libarchive와 Python libarchive-c가 필요하다.
`data/raw/`는 재생성할 수 있으므로 Git에서 제외한다. 이름을 정리한 관찰용 폴더는 `data/` 바로 아래에 둔다. 원본의 가공물에도 같은 CC BY-SA 4.0 조건을 유지한다.

## 로컬 시퀀스 이름

각 시퀀스의 시간순 대표 프레임을 확인하여 폴더명을 장면 내용으로 바꿨다. 프레임 파일명은 원본 ID와 번호를 유지한다. 기존 결과 CSV의 `sequence` 값도 아래 원본 ID에 대응한다.

| 원본 ID | 로컬 폴더 | 관찰 내용 |
| --- | --- | --- |
| `I_CA_01` | `single_1_stationary_1_red_door/` | 빨간 옷을 입은 사람이 빨간 문 앞에서 멈춘 뒤 다시 이동 |
| `I_IL_01` | `single_1_stationary_1_lighting_1_switch/` | 사람이 벽 스위치를 조작한 뒤 이동하며 실내 밝기가 변함 |
| `I_IL_02` | `single_1_stationary_1_lighting_1_blinds/` | 사람이 창가 블라인드를 올린 뒤 돌아오며 실내 밝기가 변함 |
| `I_OC_01` | `single_1_pillar_occlusion/` | 이동하는 사람이 큰 기둥 뒤에 가려졌다가 다시 나타남 |
| `I_OC_02` | `single_1_stairwell_occlusion/` | 사람이 계단을 내려와 벽 뒤로 사라졌다가 돌아와 계단을 올라감 |

## 추가 조명 변화 영상 3개

2026-09-18에 고정 카메라, 사람 이동, 큰 조명 변화가 함께 나타나는 서로 다른 사건 3개를 추가했다. 파일별 URL·크기·SHA-256·사건 수는 `data/manifests/lighting_sources.json`에 기록했다.

| 로컬 파일 | 원본 | 관찰 내용 |
| --- | --- | --- |
| `single_1_lighting_1_door.mp4` | CSIRO `human_door_8cdd.mp4` | 한 사람이 실내를 이동하는 동안 출입문을 통한 빛으로 전역 밝기가 크게 변함 |
| `single_2_lighting_2_portable_light.mp4` | CSIRO `human_light_0d2f.mp4` | 한 사람이 두 번 따로 이동하며 휴대 조명으로 밝기가 두 번 변함 |
| `single_2_stationary_1_lighting_3_switch.mp4` | Microsoft Research Wallflower `LightSwitch` | 두 사람이 시간차를 두고 등장하고, 조명이 꺼짐·켜짐·꺼짐으로 세 번 바뀌며 한 사람이 컴퓨터 앞에 앉음 |

CSIRO 두 영상은 *Light Change Dataset* v4에서 받았다. 저자 표기는 Sisi Liang, Nick Panitz, Paul Flick, Darren Baker, Marc Elmouttie, Peter Dean, Serge Lichman, James Brett이며 DOI는 10.25919/F1PM-RQ13이다. 이용 조건은 CC BY-NC-SA 4.0이다.

Wallflower 영상은 Microsoft Research License Terms에 따라 비상업·연구 목적으로만 사용할 수 있으며, 배포 시 같은 조건을 유지해야 한다. 공식 이용 조건 원문은 `WALLFLOWER_LICENSE.docx`에 보존했다. 로컬 MP4는 2026-09-18에 원본 BMP 2,715장을 5 fps로 이어 H.264로 인코딩한 가공물이다.

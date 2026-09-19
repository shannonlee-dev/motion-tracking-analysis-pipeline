# Oxford Town Centre Dataset 출처 및 이용 조건

## 파일

| 로컬 파일 | 구분 | SHA-256 |
| --- | --- | --- |
| `raw/town_centre.mp4` (배포명 `TownCentreXVID.mp4`) | Oxford Town Centre Dataset 원본 배포 영상 | `988263dd7aa8dd52f03f052d13c81d57239c6d0ef3478e9c17a10ef3d0fa41f2` |
| `inputs/target.png` | 영상 5800번 프레임에서 추출한 등록 대상 이미지 | `9be4f4424914e4f9e81fe3a441f682a80428557fbdb132eb545bda1fdf63904c` |

## 출처와 인용

- 데이터셋: **Oxford Town Centre Dataset**
- 배포처: [Academic Torrents](https://academictorrents.com/details/35e83806d9362a57be736f370c821960eb2f2a01)
- 배포 페이지 권장 인용: *Oxford Town Centre Dataset. (2020). [Data set]. Academic Torrents.*
- 원 배포 프로젝트: University of Oxford Active Vision Laboratory의 Town Centre 프로젝트
- 관련 연구: Ben Benfold and Ian Reid, *Stable Multi-Target Tracking in Real-Time Surveillance Video*, CVPR 2011.

## 라이선스 상태

확인일: 2026-09-19.

Academic Torrents 상세 페이지의 `license` 및 `terms` 항목은 비어 있으며, 별도의 오픈 라이선스 문구도 확인되지 않았다.
따라서 CC BY, CC BY-SA, MIT 또는 퍼블릭 도메인으로 간주하지 않는다. 다운로드 가능하다는 사실만으로 수정·재배포 허가가 부여되지는 않는다.

현재 저장소에서는 다음 기준을 적용한다.

- 연구·과제 수행을 위한 로컬 분석 입력으로만 사용한다.
- 원본 영상과 여기서 추출한 이미지는 Git에 커밋하거나 별도로 재배포하지 않는다.
- 보고서·결과물에서 데이터셋명과 위 출처를 표기한다.
- 공개 또는 상업적 사용이 필요하면 권리자에게 이용·재배포 허가를 별도로 확인한다.

`TownCentre_target_frame5800.png`는 원본 영상의 파생물이므로 원본의 권리 상태를 그대로 따른다.

## 재현과 저장 정책

원본 SHA-256·크기와 등록 crop은 `reference/source.json`에 기록했다.
등록 이미지는 **0-based 5800번 프레임**, `(x, y, width, height) = (1680, 452, 162, 322)`다.
`python scripts/01_setup_data.py --purpose detection`은 로컬 원본을 검증하거나 Academic Torrents 배포를 aria2c로 받고, 누락된 등록 이미지를 같은 해시로 복원한다.
이미 다운로드한 원본은 `--detection-source /path/to/TownCentreXVID.mp4`로 가져온다.

`data/detection/raw/`, `data/detection/inputs/`, `results/detection/`은 Git에서 제외한다.
리팩토링 이전 main에는 원본·이미지가 커밋되어 있었다. 현재 경로의 재추적은 막았지만 과거 Git 이력에는 남아 있다. 이력 정리는 별도 저장소 운영 작업이다.

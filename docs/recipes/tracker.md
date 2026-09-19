# Tracker 재현 명령 기록

기존 실험별 추천 설정과 수동 관찰 메모를 보존했다. 공통 실행법은 [README](../../README.md)와 [분석 보고서](../report.md)를 따른다.

## Case 01

전체 프레임 스윕 기준 추천값입니다. 작은 검출 조각은 줄이고 주인공 검출을 유지하는 균형값입니다.

```bash
python app.py --source data/tracker/inputs/01.mpg --show-mask --learning-rate 0.001 --min-area 80 --kernel-size 1 --max-distance 80 --max-missing 30 --predict-velocity
```


## 마지막에 오른쪽으로 들어가는 사람 MISSING 후 부활

 python app.py   --source data/tracker/inputs/01.mpg   --show-mask   --learning-rate 0.01   --min-area 20   --kernel-size 1   --max-distance 80   --max-missing 30 \

## Case 02

전체 프레임 스윕 기준 추천값입니다. 정지·느린 이동 구간에서 배경 흡수를 줄이는 설정입니다.

```bash
python app.py --source data/tracker/inputs/02.mpg --show-mask --learning-rate 0.0005 --min-area 80 --kernel-size 1 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 03

전체 프레임 스윕 기준 추천값입니다. 이동·정지·재이동 장면에서 작은 잡음을 억제합니다.

```bash
python app.py --source data/tracker/inputs/03.mpg --show-mask --learning-rate 0.001 --min-area 80 --kernel-size 5 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 04

전체 프레임 스윕 기준 추천값입니다. 겹침 장면의 큰 움직임과 배경 노이즈 사이의 균형값입니다.

```bash
python app.py --source data/tracker/inputs/04.mp4 --show-mask --learning-rate 0.005 --min-area 80 --kernel-size 3 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 05

전체 프레임 스윕 기준 추천값입니다. 겹침 전후의 실루엣을 보존하면서 작은 조각을 줄입니다.

```bash
python app.py --source data/tracker/inputs/05.mp4 --show-mask --learning-rate 0.0005 --min-area 80 --kernel-size 5 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 06

전체 프레임 스윕 기준 추천값입니다. 빠른 겹침·분리 장면의 검출 공백을 줄입니다.

```bash
python app.py --source data/tracker/inputs/06.mp4 --show-mask --learning-rate 0.005 --min-area 50 --kernel-size 1 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 07

전체 프레임 스윕 기준 추천값입니다. 격한 움직임에서 노이즈와 검출 유지의 균형값입니다.

```bash
python app.py --source data/tracker/inputs/07.mp4 --show-mask --learning-rate 0.0005 --min-area 80 --kernel-size 5 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 08

전체 프레임 스윕 기준 추천값입니다. 접촉 장면에서 작은 조각까지 놓치지 않도록 설정합니다.

```bash
python app.py --source data/tracker/inputs/08.mp4 --show-mask --learning-rate 0.005 --min-area 50 --kernel-size 1 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 09

전체 프레임 스윕 기준 추천값입니다. 추격 장면에서 검출 공백을 줄이면서 노이즈를 억제합니다.

```bash
python app.py --source data/tracker/inputs/09.mp4 --show-mask --learning-rate 0.005 --min-area 50 --kernel-size 3 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 10

전체 프레임 스윕 기준 추천값입니다. 교차하는 두 객체를 비교적 깨끗하게 검출합니다.

```bash
python app.py --source data/tracker/inputs/10.mp4 --show-mask --learning-rate 0.005 --min-area 80 --kernel-size 3 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 11

전체 프레임 스윕 기준 추천값입니다. 교차 장면에서 큰 객체 영역을 안정적으로 유지합니다.

```bash
python app.py --source data/tracker/inputs/11.mp4 --show-mask --learning-rate 0.001 --min-area 80 --kernel-size 5 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 12

전체 프레임 스윕 기준 추천값입니다. 조명 변화 영상에서 foreground 검출 공백을 줄입니다.

```bash
python app.py --source data/tracker/inputs/12.mp4 --show-mask --learning-rate 0.0005 --min-area 50 --kernel-size 1 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 13

전체 프레임 스윕 기준 추천값입니다. 고해상도 조명 변화에서 작은 foreground를 최대한 보존합니다.

```bash
python app.py --source data/tracker/inputs/13.mp4 --show-mask --learning-rate 0.0005 --min-area 50 --kernel-size 1 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 14

전체 프레임 스윕 기준 추천값입니다. 저해상도 영상의 작은 객체 조각을 보존합니다.

```bash
python app.py --source data/tracker/inputs/14.mp4 --show-mask --learning-rate 0.0005 --min-area 50 --kernel-size 3 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 15

전체 프레임 스윕 기준 추천값입니다. 기둥 가림 장면에서 작은 전경 조각을 보존합니다.

```bash
python app.py --source data/tracker/inputs/15.mp4 --show-mask --learning-rate 0.0005 --min-area 50 --kernel-size 1 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 16

전체 프레임 스윕 기준 추천값입니다. 계단·벽 가림 장면의 검출 공백을 줄입니다.

```bash
python app.py --source data/tracker/inputs/16.mp4 --show-mask --learning-rate 0.0005 --min-area 80 --kernel-size 3 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 17

전체 프레임 스윕 기준 추천값입니다. 블라인드 조명 변화에서 객체 foreground를 오래 유지합니다.

```bash
python app.py --source data/tracker/inputs/17.mp4 --show-mask --learning-rate 0.0005 --min-area 50 --kernel-size 1 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 18

전체 프레임 스윕 기준 추천값입니다. 스위치 조작과 정지 구간에서 foreground 유지를 우선합니다.

```bash
python app.py --source data/tracker/inputs/18.mp4 --show-mask --learning-rate 0.0005 --min-area 50 --kernel-size 1 --max-distance 80 --max-missing 30 --predict-velocity
```

## Case 19

전체 프레임 스윕 기준 추천값입니다. 빨간 문 장면에서 전경 조각과 객체 연결의 균형을 맞춥니다.

```bash
python app.py --source data/tracker/inputs/19.mp4 --show-mask --learning-rate 0.0005 --min-area 50 --kernel-size 5 --max-distance 80 --max-missing 30 --predict-velocity
```


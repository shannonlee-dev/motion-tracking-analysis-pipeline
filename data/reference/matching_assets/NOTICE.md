# OTB2015 Jogging-1 원본·이용 조건

제공 데이터: OTB-2015(Visual Tracker Benchmark)의 `Jogging [1,2]` 시퀀스.
원본을 가져온 페이지: https://rvlab.snu.ac.kr/research/tracker_benchmark

해당 페이지는 Jogging을 TB-100 시퀀스로, 속성은 `OCC`, `DEF`, `OPR`로 표시한다. 이 페이지에는 데이터 라이선스 전문이 없으므로, 저자 Yi Wu, Jongwoo Lim, Ming-Hsuan Yang 명의의 OTB2015 배포 레코드에서 확인한 **CC BY 4.0**을 적용한다.
라이선스 레코드: https://figshare.com/articles/dataset/OTB2015/24427468
라이선스 전문: https://creativecommons.org/licenses/by/4.0/

CC BY 4.0에 따라 이 저장소의 `Jogging.zip`에서 추출한 프레임·GT와 그 가공물을 재배포할 때에는 위 저자와 OTB2015를 표기하고, 라이선스 링크와 변경 사항을 함께 표시한다. 가공 내용은 다음과 같다.

- `raw/Jogging/`: 원본 ZIP을 그대로 압축 해제한 JPG·GT.
- `selected_frames/`: `target` 및 조건별 프레임 6개를 원본에서 복사.
- `data/matching_inputs/Jogging-1/`: GT bbox로 자른 PNG 6개와 JPG를 25 fps로 연결한 `jogging.mp4`.
- `results/jogging_matching/`: GT 시각화, 특징점과 매칭 결과.

원본 ZIP의 바이트 수·SHA-256·출처·인용은 `data/reference/manifests/otb_sources.json`에 기록했다. 원본 ZIP은 `data/raw/OTB/Jogging.zip`에 두며, 재생성 가능한 원본이므로 Git에서 제외한다. 원본 JPG·GT와 선택 근거는 이 폴더에 보관한다.

인용: Y. Wu, J. Lim, and M.-H. Yang, “Object Tracking Benchmark,” *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 37(9), 1834–1848, 2015. DOI: 10.1109/TPAMI.2014.2388226.

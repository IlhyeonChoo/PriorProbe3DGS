# Data Layout

이 디렉토리는 실데이터를 버전관리하지 않는다. 대신 실제 학습을 위한 표준 경로와 템플릿만 추적한다.

## Layout

- `data/_downloads/`
  - 라이선스/로그인 제약이 있는 원본 다운로드를 두는 곳
- `data/public_datasets/`
  - vanilla 3DGS가 바로 읽는 processed subset scene root를 두는 곳
- `data/priors/`
  - ShapeSplat prior asset과 retrieval feature를 두는 곳

## Training Contract

- Replica/ScanNet 실학습 입력은 `images/ + sparse/0/`를 갖춘 processed scene root다.
- raw dataset direct loader는 현재 레포에서 지원하지 않는다.
- `scripts/check_training_prereqs.py`를 실행하면 prior placeholder와 dataset 준비 상태를 함께 확인할 수 있다.

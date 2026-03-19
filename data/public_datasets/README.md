# Processed Public Datasets

이 아래 경로는 vanilla 3DGS가 바로 읽는 processed scene root다.

각 scene 디렉토리는 최소한 아래를 포함해야 한다.

- `images/`
- `sparse/0/`
- `scene_meta.json`

선택 항목:

- `masks/`

`scripts/resolve_dataset_scene.py --check`와 `scripts/check_training_prereqs.py`는 이 레이아웃을 기준으로 점검한다.

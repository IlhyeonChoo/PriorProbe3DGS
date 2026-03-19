# Prior Assets

ShapeSplat prior asset과 retrieval feature는 이 아래에 둔다.

현재 `configs/priors/shapesplat.yaml`의 기본 object들은 `placeholder: true`로 표시되어 있다. 실제 학습 전에 아래를 교체해야 한다.

- `data/priors/shapesplat/<object_id>.ply`
- `data/priors/shapesplat/<object_id>.npy` (automatic retrieval을 쓸 경우)

교체 후 `scripts/prepare_prior_library.py --config configs/priors/shapesplat.yaml`를 다시 실행한다.

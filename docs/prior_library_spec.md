# Prior Library Spec

Prior library manifest는 JSON 파일 하나로 저장한다.

## Entry Schema

- `object_id`: prior object 식별자
- `category`: semantic category
- `gaussian_path`: object Gaussian asset 경로
- `feature_path`: retrieval feature 경로
- `placeholder`: 실제 학습 전에 교체해야 하는 scaffold asset 여부
- `metadata.source`: prior 출처
- `metadata.scale_meters`: metric scale
- `metadata.tags`: 실험용 태그

## Expected Workflow

1. `configs/priors/shapesplat.yaml`에서 seed prior 집합을 정의한다.
2. `scripts/prepare_prior_library.py`가 manifest를 초기 생성한다.
3. `scripts/add_domain_objects.py`가 도메인 객체를 manifest에 증분 추가한다.
4. `scripts/run_experiment.py --config configs/experiments/oracle_prior_vanilla_3dgs.yaml`가 top-1 prior를 선택해 vanilla 3DGS prior-init backend로 넘긴다.

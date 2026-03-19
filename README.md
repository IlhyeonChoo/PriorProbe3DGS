# PriorProbe3DGS

PriorProbe3DGS는 사전 학습된 3D Gaussian Splatting(3DGS) object prior가 장면 최적화 시간을 실제로 단축하는지 통제된 환경에서 검증하기 위한 1단계 연구 레포지토리다.

현재 레포는 연구 계획 문서에 맞춘 초기 골격을 포함한다. 구현은 placeholder 수준이지만, 디렉토리 구조, 설정 파일, 스크립트 진입점, 패키지 인터페이스는 바로 확장할 수 있게 정리되어 있다.

## Research Questions

1. 도메인 증분 prior가 from-scratch 3DGS 대비 optimization time과 time-to-target quality를 감소시키는가?
2. occlusion 강도에 따라 prior 재사용 효과가 어떻게 달라지는가?
3. ShapeSplat 그대로 사용, 객체 증분 추가, 경량 추가학습 중 어느 전략이 가장 실용적인가?
4. 성능이 기대에 미치지 못할 경우, 병목이 prior 품질인지 retrieval 품질인지 insertion 품질인지?

## Repository Layout

```text
PriorProbe3DGS/
├── configs/
│   ├── base/
│   ├── datasets/
│   ├── priors/
│   └── experiments/
├── src/
│   └── priorprobe/
│       ├── prior_library/
│       ├── retrieval/
│       ├── insertion/
│       ├── optimization/
│       ├── evaluation/
│       └── scene/
├── scripts/
├── notebooks/
├── docs/
├── manuscript/
├── outputs/
├── logs/
└── tests/
```

## Current Scaffold

- `configs/`에는 baseline, oracle, domain-incremental 실험용 YAML 템플릿이 있다.
- `src/priorprobe/`에는 prior library, retrieval, insertion, optimization, evaluation, controlled scene용 최소 인터페이스가 있다.
- `scripts/`에는 prior manifest 생성, 도메인 객체 추가, 실험 실행, 평가, 결과 export용 placeholder CLI가 있다.
- `scripts/train_vanilla_3dgs_backend.py`는 외부 `gaussian-splatting` 레포를 수정하지 않고 prior-initialized 학습 경로를 붙이는 wrapper다.
- `configs/datasets/`와 `scripts/resolve_dataset_scene.py`는 ShapeSplat object split, Replica, ScanNet, NeRF Synthetic 같은 공개 데이터셋을 target scene으로 해석하는 템플릿과 점검 CLI를 제공한다.
- `scripts/check_training_prereqs.py`는 실제 학습 전에 prior placeholder 교체 여부와 Replica/ScanNet subset 준비 상태를 함께 점검한다.
- `tests/`에는 prior library manifest round-trip을 검증하는 기본 테스트가 있다.

## Quick Start

```bash
uv python pin 3.11
uv sync

uv run python scripts/prepare_prior_library.py --config configs/priors/shapesplat.yaml
uv run python scripts/run_experiment.py --config configs/experiments/baseline_from_scratch.yaml
uv run python scripts/run_experiment.py --config configs/experiments/oracle_prior.yaml

# vanilla 3DGS backend dry-run 예시
uv run python scripts/run_experiment.py \
  --config configs/experiments/oracle_prior_vanilla_3dgs.yaml \
  --dataset-scene-id room_0 \
  --dataset-root /abs/path/to/replica_colmap \
  --dry-run

# dataset config 해석 확인
uv run python scripts/resolve_dataset_scene.py \
  --config configs/datasets/scannet.yaml \
  --scene-id scene0000_00

# 실제 학습 전 준비 상태 확인
uv run python scripts/check_training_prereqs.py
```

## Notes

- 상세한 연구 배경과 1단계/2단계 관계는 `PriorProbe3DGS_README.md` 및 `research_plan.md`에 정리되어 있다.
- 현재 스크립트는 연구 흐름을 고정하기 위한 scaffold이며, 실제 3DGS 학습 코드는 이후 단계에서 연결하면 된다.
- PyTorch는 공식 `cu128` wheel index에 고정되어 있어 `uv sync` 시 CUDA 12.8 빌드가 설치된다.
- vanilla 3DGS prior-init 경로는 외부 `../3DGS/gaussian-splatting`와 그 전용 Python 환경을 사용한다.
- `configs/datasets/`의 dataset은 reconstruction target용이다. prior source는 `configs/priors/shapesplat.yaml`에서 따로 관리한다.
- `configs/experiments/*vanilla_3dgs.yaml`의 `model_path`는 placeholder로 두고, 실제 기본 출력 경로는 `outputs/backend_runs/<experiment>/<scene_id>`로 자동 생성되게 맞춰뒀다.
- `data/priors/shapesplat/*.ply`는 스캐폴드 검증용 placeholder prior다. 실제 ShapeSplat export를 확보하면 같은 경로에 교체하면 된다.
- `data/` 아래에는 raw download root와 processed 3DGS subset root를 모두 scaffold로 잡아뒀다. 실데이터는 계속 git ignore되고 README, `.gitkeep`, `scene_meta.json` 템플릿만 추적된다.

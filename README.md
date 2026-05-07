# PriorProbe3DGS

PriorProbe3DGS는 사전 학습된 3D Gaussian Splatting(3DGS) object prior가 장면 최적화 시간을 실제로 단축하는지 통제된 환경에서 검증하기 위한 연구 레포지토리다.

핵심 질문은 단순하다: **도메인 보강된 prior를 재사용하면 from-scratch 3DGS보다 빠르게 같은 품질에 도달하는가?**

이 레포는 [ReCompose3D](https://github.com/CNU26-3DGS/ReCompose3D) 프로젝트의 1단계 연구에 해당하며, 여기서 검증된 prior 전략은 2단계(ReCompose3D)에서 가속축 결합 파이프라인의 기반으로 사용된다.

## Research Questions

1. 도메인 증분 prior가 from-scratch 3DGS 대비 optimization time과 time-to-target quality를 감소시키는가?
2. occlusion 강도에 따라 prior 재사용 효과가 어떻게 달라지는가?
3. ShapeSplat 그대로 사용, 객체 증분 추가, 경량 추가학습 중 어느 전략이 가장 실용적인가?
4. 성능이 기대에 미치지 못할 경우, 병목이 prior 품질인지 retrieval 품질인지 insertion 품질인지?

## Experimental Design

### Comparison Groups (실행 순서)

총 6개 비교군을 순차적으로 실행하여 원인을 단계적으로 분리한다.

| 순위 | 비교군 | 목적 |
|------|--------|------|
| 1 | from-scratch 3DGS | baseline |
| 1 | oracle prior | prior 재사용의 원리적 효과 확인 |
| 2 | oracle prior + oracle alignment | 성능 상한선 확인 |
| 3 | ShapeSplat 기본 prior + 자동 alignment | 자동화 gap 측정 |
| 4 | 도메인 증분 prior + 자동 alignment | 도메인 보강 효과 |
| 4 | 도메인 증분 prior + 경량 적응 | 추가학습 필요성 판단 |

oracle prior는 아래 3개 조건으로 단계적으로 세분화한다.

| 조건 | 설명 | 목적 |
|------|------|------|
| A | Oracle Prior + Oracle Alignment | 이론적 상한선 (ceiling) |
| B | 동일 객체 lib 보유 + 자동 retrieval/insertion | 이상적 조건 자동화 성능 |
| C | 동일 객체 lib 미보유 (유사 객체 매칭) | 현실적 시나리오 성능 |

### Data Strategy

- **Phase A:** 공개 데이터셋(Replica, ScanNet 등) 기반의 단순 실내 장면
- **Phase B:** 직접 촬영한 실내 장면으로 도메인 일치도가 높은 조건 추가

### Key Metrics

- **Primary:** total optimization time, time-to-target quality
  - vanilla 수렴 품질 기준 80% / 90% / 95% 도달 wall-clock time (상대값 기준)
  - 30K iter 고정 시 PSNR/SSIM/LPIPS
- **Secondary:** retrieval accuracy, alignment success rate, Gaussian count

## Vanilla 3DGS Backend

- 바닐라 3DGS는 개인 fork 레포에 고정하여 사용한다.
- Fork URL 및 commit hash: 추후 기록 예정
- `scripts/train_vanilla_3dgs_backend.py`는 실행 시 backend 레포의 commit hash를 로그에 자동 출력한다.

## Repository Layout

```text
PriorProbe3DGS/
├── configs/
│   ├── base/                  # 프로젝트 공통 설정
│   │   └── project.yaml
│   ├── datasets/              # 데이터셋별 설정
│   │   ├── replica.yaml
│   │   └── custom_capture.yaml
│   ├── priors/                # prior 라이브러리 연결 설정
│   │   └── shapesplat.yaml
│   └── experiments/           # 실험별 설정
│       ├── baseline_from_scratch.yaml
│       ├── oracle_prior.yaml
│       ├── oracle_alignment.yaml
│       ├── shapesplat_auto.yaml
│       ├── domain_incremental.yaml
│       └── domain_incremental_adapted.yaml
├── src/
│   └── priorprobe/
│       ├── __init__.py
│       ├── prior_library/     # prior 라이브러리 관리 및 증분 추가
│       ├── retrieval/         # 객체 검색 (OpenCLIP coarse + ShapeSplat fine)
│       ├── insertion/         # 객체 삽입 및 정렬
│       ├── optimization/      # 3DGS 최적화 래퍼
│       ├── evaluation/        # 평가 지표 계산
│       └── scene/             # 장면 구성 및 occlusion 통제
├── scripts/
├── notebooks/
├── docs/
│   ├── experiment_design.md   # 실험 설계 상세
│   └── prior_library_spec.md  # prior 라이브러리 구성 명세
├── manuscript/
│   └── outline.md
├── outputs/                   # 실험 산출물 (gitignored)
├── logs/                      # 실행 로그 (gitignored)
├── tests/
│   └── test_prior_library.py
├── .gitignore
├── pyproject.toml
├── README.md
└── LICENSE
```

## Directory Intent

- **`src/priorprobe/prior_library`** — ShapeSplat 기반 prior index를 관리한다. 도메인 객체를 증분 추가하는 로직과 각 객체의 보조 메타데이터(크기 정보 등)를 여기서 처리한다.
- **`src/priorprobe/retrieval`** — OpenCLIP(coarse) + ShapeSplat feature(fine) 2단계 매칭으로 prior를 검색한다. oracle retrieval 조건도 여기서 구현한다.
- **`src/priorprobe/insertion`** — 검색된 prior를 장면에 삽입하고 pose를 정렬한다. oracle alignment과 자동 alignment을 분리하여 제공한다.
- **`src/priorprobe/optimization`** — from-scratch 3DGS와 prior-initialized 3DGS 학습 루프를 공통 인터페이스로 감싼다. optimizer, densification, learning rate schedule은 모든 비교군에서 동일하게 유지한다.
- **`src/priorprobe/evaluation`** — 핵심 지표(total time, time-to-target quality)와 보조 지표를 계산한다.
- **`src/priorprobe/scene`** — controlled scene 설정과 occlusion 수준 정량화를 담당한다.
- **`configs/experiments`** — 비교군 6개에 대응하는 실험 설정 파일을 두어 재현성을 보장한다.
- **`docs`** — 실험 설계 결정과 prior 라이브러리 명세를 기록한다.
- **`manuscript`** — 논문 작성을 위한 초안과 메모를 관리한다.

## Workflow

```
Input Images → SfM → Object Segmentation → Feature Extraction
                                                    ↓
                                        Prior Library (ShapeSplat + domain objects)
                                                    ↓
                                    Object Retrieval (OpenCLIP coarse → ShapeSplat fine)
                                                    ↓
                                        Object Insertion & Alignment (or oracle)
                                                    ↓
                                    Scene Composition (prior Gaussians + background)
                                                    ↓
                                            Joint Optimization
                                                    ↓
                                    Evaluation (time, quality, diagnostics)
```

## Relationship to ReCompose3D

| | PriorProbe3DGS (1단계) | ReCompose3D (2단계) |
|---|---|---|
| **질문** | prior 재사용이 효과가 있는가? | prior + 가속축 결합이 시스템 수준에서 유효한가? |
| **장면** | controlled (단순 배경, 소수 객체) | 복잡한 실내 (clutter, 다수 객체) |
| **prior** | 탐색 및 검증 대상 | 1단계에서 검증된 전략을 고정 |
| **novelty** | prior 효과 분리 및 진단 | 가속축 결합의 Pareto 분석 |
| **관계** | 독립 완결 연구 | 1단계 코드를 dependency로 참조 |

## Prerequisites

- Python 3.11+
- CUDA 12.8
- PyTorch 2.7+
- GPU: NVIDIA RTX PRO 4500 32GB 기준

## Getting Started

```bash
uv python pin 3.11
uv sync

# prior 라이브러리 초기화
uv run python scripts/prepare_prior_library.py --config configs/priors/shapesplat.yaml

# baseline 실험 실행
uv run python scripts/run_experiment.py --config configs/experiments/baseline_from_scratch.yaml

# oracle prior 실험 실행
uv run python scripts/run_experiment.py --config configs/experiments/oracle_prior.yaml

# vanilla 3DGS backend dry-run 예시
uv run python scripts/run_experiment.py \
  --config configs/experiments/oracle_prior_vanilla_3dgs.yaml \
  --dataset-scene-id room_0 \
  --dataset-root /abs/path/to/replica_colmap \
  --dry-run
```

## Citation

관련 문의는 GitHub Issues를 통해 가능하다.

## License

TBD

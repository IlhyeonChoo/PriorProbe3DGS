# Replica Gaussian-Direct Surface RGB Baseline Determinism Plan

Date: 2026-03-31

## 목적

`surface_rgb_baseline_15000_variance01~10` 반복 실험에서 확인된 baseline 분산의 주요 원인을 정리하고, 이를 줄이기 위한 코드 수정과 후속 검증 절차를 문서화한다.

핵심 질문:

1. 왜 동일 조건 baseline 반복에서 최종 품질 차이가 `~1.1~1.35 dB`까지 벌어졌는가?
2. 어떤 수정이 필요하며, 어느 수준까지 분산이 줄어들면 "비교 기준선으로 충분히 안정적"하다고 볼 수 있는가?

---

## 관찰 요약

참고 보고서:

- `docs/experiment_results/03-27_baseline_surface_rgb_variance10_2026.md`
- `outputs/gaussian_direct/reports/replica_gaussian_direct_surface_rgb_baseline_variance10_summary.csv`
- `outputs/gaussian_direct/reports/replica_gaussian_direct_surface_rgb_baseline_variance10_per_run.csv`

반복 실험 결과:

- `room_0`: PSNR mean `46.689600`, std `0.370861`, min `45.902729`, max `47.250519`, range `1.347790`
- `office_0`: PSNR mean `44.123923`, std `0.351150`, min `43.433895`, max `44.558788`, range `1.124893`

최고/최저 run 예시:

- `room_0`
  - best: `surface_rgb_baseline_15000_variance04` -> `47.250519`
  - worst: `surface_rgb_baseline_15000_variance08` -> `45.902729`
- `office_0`
  - best: `surface_rgb_baseline_15000_variance10` -> `44.558788`
  - worst: `surface_rgb_baseline_15000_variance06` -> `43.433895`

패턴:

- `room_0`는 `10k`까지 비슷하거나 worst가 일시적으로 더 높다가, 마지막 `10k -> 15k` 구간에서 크게 갈린다.
- `office_0`는 `2k~3k`부터 차이가 벌어진다.
- 최종 Gaussian 수는 best/worst 사이에 큰 차이가 없다.
- 즉 단순히 "더 많은 Gaussian을 만들었기 때문"이라기보다, **초기/중기 optimization path가 달라져 다른 구조적 상태로 수렴했다**고 보는 편이 타당하다.

---

## 현재 원인 가설

현재 1순위 가설은 **camera ordering 및 학습 경로의 비결정성**이다.

근거:

1. wrapper script `scripts/train_vanilla_3dgs_backend.py`는 camera list를 shuffle한다.
2. 그러나 upstream `train.py`가 호출하는 `safe_state()`에 해당하는 seed 고정이 wrapper 경로에는 없다.
3. 따라서 동일한 image/pose 집합을 사용하더라도, 각 run의 학습 순서와 gradient accumulation 경로가 달라질 수 있다.

관련 코드 위치:

- `scripts/train_vanilla_3dgs_backend.py`
  - `random.shuffle(train_cam_infos)` / `random.shuffle(test_cam_infos)` at lines `1191-1195`
  - wrapper `main()` entry at lines `1517+`
  - 이 경로에서는 `safe_state()` 또는 동등한 seed 초기화 호출이 없음
- `../3DGS/gaussian-splatting/train.py`
  - `safe_state(args.quiet)` at line `312`
- `../3DGS/gaussian-splatting/utils/general_utils.py`
  - `random.seed(0)`, `np.random.seed(0)`, `torch.manual_seed(0)` at lines `130-132`

해석:

- image/pose **집합 자체가 매번 다시 샘플링된 증거는 현재 없음**
- 대신 **같은 image/pose를 어떤 순서로 최적화에 사용하느냐가 run마다 달라졌을 가능성**이 높다
- 3DGS는 단순 연속 최적화만이 아니라 densify/prune 경로가 얽혀 있으므로, 초반 작은 차이가 후반 구조 차이로 확대될 수 있다

---

## 필요한 수정

### 수정 1. Wrapper에서 명시적으로 seed를 고정

파일:

- `scripts/train_vanilla_3dgs_backend.py`

필요 사항:

1. wrapper 인자로 전역 seed를 받는다
2. `random`, `numpy`, `torch`, `torch.cuda`에 동일한 seed를 적용한다
3. camera shuffle 전에 seed를 반드시 적용한다
4. 가능하면 실행 metadata에 실제 seed 값을 기록한다

권장 구현 방향:

```python
parser.add_argument("--seed", type=int, default=42)
```

그리고 `main()`에서 training 시작 전:

```python
import random
import numpy as np
import torch

random.seed(args.seed)
np.random.seed(args.seed)
torch.manual_seed(args.seed)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(args.seed)
```

주의:

- 현재 upstream `safe_state()`는 `torch.cuda.set_device(cuda:0)`까지 같이 수행한다.
- wrapper에서는 seed 초기화만 가져오고, device 강제 고정은 현 브랜치 정책에 맞게 별도 판단하는 것이 낫다.
- 이유: multi-GPU/portable 실행 환경에서는 단순 seed 고정과 device 고정은 분리하는 편이 안전하다.

### 수정 2. Camera ordering seed를 metadata에 남기기

같은 파일에서 아래 정보가 `backend_run.json`에 드러나도록 남기는 것이 좋다.

- `seed`
- `camera_order_seed`
- `camera_shuffle_enabled`

권장 정책:

- 별도 인자를 두지 않는다면 `camera_order_seed = seed`
- 이후 카메라 선택 서브샘플링을 추가할 가능성을 고려하면, 전역 seed와 camera order seed를 분리해도 된다

예시:

```python
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--camera-order-seed", type=int, default=None)
```

`None`이면 내부에서 `camera_order_seed = seed`로 보정.

### 수정 3. 가능하면 deterministic mode를 명시적으로 지원

엄격한 재현성을 원하면 아래 옵션도 검토할 수 있다.

```python
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
```

다만 이 옵션은 성능 저하와 일부 연산 제약을 만들 수 있으므로 기본값으로 강제할지, `--deterministic` 플래그로 둘지는 분리 판단이 필요하다.

현재 우선순위는:

1. Python / NumPy / Torch seed 고정
2. camera ordering 고정
3. 그 이후에도 분산이 남으면 cuDNN deterministic 옵션 검토

### 수정 4. Experiment config 또는 runner에서 seed를 드러내기

현재 `variance01~10` config는 이름만 다르고 실질 설정은 같다. 이후 재현 실험에서는 seed가 명시적으로 보여야 한다.

권장 방식 중 하나:

- 방법 A: runner에서 `--seed <N>`를 직접 넘긴다
- 방법 B: experiment config에 seed field를 추가하고 backend 호출로 전달한다

재현성 관점에서는 **config 또는 backend_run.json에서 seed를 바로 확인할 수 있어야** 한다.

---

## 수정 후 테스트 계획

### Phase 1. 동일 seed 반복 일치성 확인

목적:

- seed 고정이 실제로 camera ordering과 학습 경로를 안정화하는지 확인

실험:

- baseline config: `gaussian_direct_surface_rgb_baseline_15000`
- scene: `room_0`, `office_0`
- seed: `42`
- 동일 조건으로 3회 반복 실행

기대:

- 최종 PSNR/SSIM/LPIPS가 완전히 같거나, 최소한 floating-point noise 수준으로만 다를 것
- checkpoint별 `gaussian_count`와 주요 metric 곡선도 사실상 동일할 것

판정 기준:

- strong pass:
  - final PSNR 차이 `< 0.01 dB`
  - final SSIM 차이 `< 1e-4`
  - final LPIPS 차이 `< 1e-4`
- weak pass:
  - final PSNR 차이 `< 0.03 dB`
  - 기존 `0.35 dB` std와 비교하면 충분히 큰 개선

만약 여기서도 차이가 크면:

- seed 고정만으로는 부족하다는 뜻
- cuDNN deterministic 또는 upstream training 내부 비결정성 지점을 추가로 확인해야 한다

### Phase 2. 서로 다른 seed 간 baseline 분산 측정

목적:

- "완전 동일 seed 재현성"과 "서로 다른 seed에 대한 baseline 분산"을 분리해서 본다

실험:

- 동일 config, 동일 scene
- seed만 `41, 42, 43, 44, 45` 등으로 바꿔 5회 실행

왜 필요한가:

- 고정 seed 재현성만 확인하면 "코드는 재현 가능"하다는 것만 알 수 있다
- 그러나 실제 baseline 비교에서는 **seed 변화에 대한 민감도**도 알아야 한다

기대:

- 분산이 10회 배치 대비 줄거나, 최소한 "어떤 범위까지가 정상 seed variance인지"를 수치로 정의할 수 있어야 한다

판정 기준:

- 기존 batch 기준:
  - `room_0 std = 0.370861`
  - `office_0 std = 0.351150`
- 목표:
  - 먼저 동일 seed 반복 분산을 거의 0에 가깝게 만든다
  - 그 다음 서로 다른 seed 기준 std가 실제 baseline sensitivity로 얼마인지 다시 측정한다

### Phase 3. prior-vs-baseline 비교 규칙 갱신

목적:

- 이후 prior 실험의 개선폭 해석 기준을 정한다

실험 해석 규칙:

- baseline variance보다 작은 delta는 "개선"으로 단정하지 않는다
- baseline seed variance를 새로 측정한 뒤, 아래처럼 rule을 둔다

예시:

- `delta < 0.5 * baseline_std`: no evidence
- `0.5 * std <= delta < 1.0 * std`: weak signal
- `delta >= 1.0 * std`: candidate improvement
- `delta >= 2.0 * std`: strong candidate improvement

정확한 threshold는 새 baseline variance 측정 후 확정한다.

---

## 권장 실행 순서

1. `scripts/train_vanilla_3dgs_backend.py`에 seed 고정 추가
2. `backend_run.json`에 seed 기록 추가
3. 동일 seed 3회 반복으로 재현성 확인
4. seed sweep 5회로 baseline variance 재측정
5. 이후 prior 실험 해석 기준 업데이트

---

## 리스크와 주의사항

### 1. Seed 고정만으로 완전 재현이 안 될 수 있음

CUDA kernel, fused op, cuDNN 알고리즘 선택 등으로 인해 일부 비결정성이 남을 수 있다.

이 경우 해야 할 일:

- deterministic flag 추가 검토
- upstream 3DGS training loop 내부에서 추가 난수 사용 여부 점검
- checkpoint-level diff로 divergence 시작 시점 재확인

### 2. 성능과 재현성의 trade-off

엄격 deterministic mode는 속도를 늦출 수 있다.

권장 정책:

- 기본 연구용 baseline 비교는 deterministic 우선
- 대규모 sweep에서는 필요시 fast mode와 deterministic mode를 분리

### 3. 기존 결론 재해석 필요

현재 baseline variance가 꽤 크므로, `0.05~0.1 dB` 수준의 prior 개선은 재현성 확보 전에는 강한 근거로 쓰기 어렵다.

특히 surface RGB 계열에서는:

- baseline 분산을 먼저 안정화한 뒤
- prior 실험의 delta를 다시 읽는 순서가 필요하다

---

## 다음 액션

코드 수정 이후 바로 아래 두 묶음을 실행한다.

1. deterministic sanity check
   - baseline
   - `room_0`, `office_0`
   - same seed x3

2. seed sensitivity check
   - baseline
   - `room_0`, `office_0`
   - different seeds x5

이 두 단계가 끝나야 이후 prior 실험의 작은 품질 차이를 의미 있게 해석할 수 있다.

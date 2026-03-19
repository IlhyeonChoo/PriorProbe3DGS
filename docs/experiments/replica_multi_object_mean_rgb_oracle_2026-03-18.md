# Replica Multi-Object Mean-RGB Oracle vs Baseline and CLIP

Date: 2026-03-18

## Setup

- Dataset: Replica scene-centric multi-object exports on shared SSD
- Scenes: `room_0`, `office_0`
- Target selection: categories `chair`, `sofa`, `table`, `lamp` within each scene, top-4 objects by volume
- Retrieval feature: `mean_rgb`
- Prior library: ShapeSplat ModelNet bundle
  - `chair`: 256 priors
  - `sofa`: 256 priors
  - `table`: 256 priors
  - `lamp`: 123 priors
- Reconstruction backend: vanilla 3DGS
- Insertion mode: oracle alignment + multi-prior `merge` init
- Execution order: `room_0`, `office_0` sequential
- Baseline and CLIP multi-object references:
  [replica_multi_object_clip_oracle_2026-03-17.md](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS/docs/experiments/replica_multi_object_clip_oracle_2026-03-17.md)

## Results

### room_0

- Baseline multi
  - PSNR@7000: `13.3091`
  - SSIM@7000: `0.6249`
  - LPIPS@7000: `0.3059`
  - Total optimization time: `139.17s`
  - Baseline 3000-iter PSNR target: `12.8673`
  - Time to target: `59.64s` at `3000`
- CLIP multi
  - Selected priors: `lamp_0085`, `sofa_0131`, `sofa_0195`, `chair_0016`
  - PSNR@7000: `13.3182`
  - SSIM@7000: `0.6271`
  - LPIPS@7000: `0.3042`
  - Total optimization time: `148.96s`
  - Time to same target: `106.40s` at `5000`
- Mean-RGB multi
  - Selected priors: `lamp_0019`, `sofa_0003`, `sofa_0003`, `chair_0201`
  - Mean retrieval score: `0.9997`
  - PSNR@7000: `13.3023`
  - SSIM@7000: `0.6266`
  - LPIPS@7000: `0.3040`
  - Total optimization time: `148.27s`
  - Time to same target: `105.91s` at `5000`
- Delta vs baseline
  - PSNR: `-0.0068`
  - SSIM: `+0.0017`
  - LPIPS: `-0.0019`
- Delta vs CLIP
  - PSNR: `-0.0159`
  - SSIM: `-0.0005`
  - LPIPS: `-0.0002`

### office_0

- Baseline multi
  - PSNR@7000: `12.9721`
  - SSIM@7000: `0.5606`
  - LPIPS@7000: `0.3631`
  - Total optimization time: `146.48s`
  - Baseline 3000-iter PSNR target: `12.4943`
  - Time to target: `62.78s` at `3000`
- CLIP multi
  - Selected priors: `sofa_0131`, `sofa_0131`, `table_0230`, `chair_0239`
  - PSNR@7000: `12.9827`
  - SSIM@7000: `0.5608`
  - LPIPS@7000: `0.3653`
  - Total optimization time: `154.72s`
  - Time to same target: `66.31s` at `3000`
- Mean-RGB multi
  - Selected priors: `sofa_0003`, `sofa_0050`, `table_0020`, `chair_0240`
  - Mean retrieval score: `0.9947`
  - PSNR@7000: `12.9568`
  - SSIM@7000: `0.5584`
  - LPIPS@7000: `0.3662`
  - Total optimization time: `153.38s`
  - Time to same target: `65.73s` at `3000`
- Delta vs baseline
  - PSNR: `-0.0153`
  - SSIM: `-0.0022`
  - LPIPS: `+0.0031`
- Delta vs CLIP
  - PSNR: `-0.0259`
  - SSIM: `-0.0024`
  - LPIPS: `+0.0010`

## Takeaways

- Under the current multi-object setup, `mean_rgb` did not outperform the existing `CLIP` multi-object retrieval.
- `room_0`에서는 mean-rgb가 baseline보다 PSNR은 약간 낮았지만 SSIM/LPIPS는 약간 좋아졌다. 다만 time-to-target은 baseline보다 훨씬 느렸다.
- `office_0`에서는 mean-rgb가 baseline과 CLIP 모두보다 전반적으로 약했다.
- mean-rgb의 retrieval score는 매우 높게 나왔지만, 실제 reconstruction 품질로 연결되지는 않았다.
- 현재 결과만 보면 multi-object에서도 retrieval feature는 `mean_rgb < CLIP`이고, 둘 다 vanilla baseline보다 수렴 속도를 개선하지 못했다.

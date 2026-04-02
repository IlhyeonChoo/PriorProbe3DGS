# Replica Multi-Object CLIP Oracle vs Vanilla 3DGS

Date: 2026-03-17

## Setup

- Dataset: Replica scene-centric multi-object exports on shared SSD
- Scenes: `room_0`, `office_0`
- Target selection: categories `chair`, `sofa`, `table`, `lamp` within each scene, top-4 objects by volume
- Query feature: `open_clip` `ViT-B-32` / `laion2b_s34b_b79k`
- Prior library: ShapeSplat ModelNet bundle
  - `chair`: 256 priors
  - `sofa`: 256 priors
  - `table`: 256 priors
  - `lamp`: 123 priors
- Reconstruction backend: vanilla 3DGS
- Insertion mode: oracle alignment + multi-prior `merge` init
- Execution order: all four runs executed sequentially to keep timing comparisons fair

## Selected Targets

### room_0

- `lamp`: object `6`
- `sofa`: object `9`
- `sofa`: object `77`
- `chair`: object `74`

### office_0

- `sofa`: object `9`
- `sofa`: object `7`
- `table`: object `58`
- `chair`: object `61`

## Results

### room_0

- Multi-object vanilla baseline
  - PSNR@7000: `13.3091`
  - SSIM@7000: `0.6249`
  - LPIPS@7000: `0.3059`
  - Total optimization time: `139.17s`
  - Baseline 3000-iter PSNR target: `12.8673`
  - Time to target: `59.64s` at `3000`
- Multi-object oracle prior
  - Selected priors: `lamp_0085`, `sofa_0131`, `sofa_0195`, `chair_0016`
  - PSNR@7000: `13.3182`
  - SSIM@7000: `0.6271`
  - LPIPS@7000: `0.3042`
  - Total optimization time: `148.96s`
  - Time to same target: `106.40s` at `5000`
- Delta
  - PSNR: `+0.0092`
  - SSIM: `+0.0022`
  - LPIPS: `-0.0018`

### office_0

- Multi-object vanilla baseline
  - PSNR@7000: `12.9721`
  - SSIM@7000: `0.5606`
  - LPIPS@7000: `0.3631`
  - Total optimization time: `146.48s`
  - Baseline 3000-iter PSNR target: `12.4943`
  - Time to target: `62.78s` at `3000`
- Multi-object oracle prior
  - Selected priors: `sofa_0131`, `sofa_0131`, `table_0230`, `chair_0239`
  - PSNR@7000: `12.9827`
  - SSIM@7000: `0.5608`
  - LPIPS@7000: `0.3653`
  - Total optimization time: `154.72s`
  - Time to same target: `66.31s` at `3000`
- Delta
  - PSNR: `+0.0106`
  - SSIM: `+0.0002`
  - LPIPS: `+0.0023`

## Takeaways

- Multi-object prior insertion improved final PSNR slightly in both scenes.
- `room_0` improved in all three final-quality metrics, but it reached the baseline 3000-iter PSNR target materially later than vanilla.
- `office_0` showed a small final PSNR/SSIM gain, but LPIPS regressed slightly and time-to-target was still slower than vanilla.
- Under this scene-centric multi-object setup, adding more priors did not reverse the earlier speed issue; the main effect remained a small final-quality gain rather than faster convergence.
- Single-object and multi-object absolute scores should not be compared directly because they use different Replica export protocols: target-centric vs scene-centric.

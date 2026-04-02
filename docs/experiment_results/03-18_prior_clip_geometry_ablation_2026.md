# Replica Multi-Object CLIP+Geometry Retrieval and Insertion Ablation

Date: 2026-03-18

## Setup

- Dataset: Replica scene-centric multi-object exports on shared SSD
- Scenes: `room_0`, `office_0`
- Target selection: categories `chair`, `sofa`, `table`, `lamp` within each scene, top-4 objects by volume
- Prior library: ShapeSplat ModelNet bundle
  - `chair`: 256 priors
  - `sofa`: 256 priors
  - `table`: 256 priors
  - `lamp`: 123 priors
- Retrieval variants compared:
  - `CLIP` multi-object `merge`
  - `mean_rgb` multi-object `merge`
  - `CLIP+geometry` multi-object `merge`
  - `CLIP+geometry` multi-object `weighted_merge`
  - `CLIP+geometry` multi-object `filtered_merge`
- Reconstruction backend: vanilla 3DGS
- Target metric for convergence: baseline `3000`-iteration PSNR per scene

## Implementation Note

- The first `weighted_merge` and `filtered_merge` runs exposed an `init_mode` propagation bug in [train_vanilla_3dgs_backend.py](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS/scripts/train_vanilla_3dgs_backend.py), where the backend defaulted back to `merge`.
- The fix was to propagate `args.init_mode` into the runtime dataset object before scene construction.
- All `clip_geom weighted_merge` and `clip_geom filtered_merge` numbers below are from reruns after that fix.

## Domain-Gap Note

- Working hypothesis only: ShapeSplat priors come from synthetic CAD/object renders, while this benchmark uses Replica scenes rendered as realistic indoor environments.
- This domain gap is not treated as an experimental variable in this report.
- Follow-up: rerun the same retrieval and insertion ablations on a CAD-based synthetic indoor dataset once it is available.

## Results

### room_0

- Baseline multi
  - PSNR@7000: `13.3091`
  - SSIM@7000: `0.6249`
  - LPIPS@7000: `0.3059`
  - Total optimization time: `139.17s`
  - Baseline 3000-iter PSNR target: `12.8673`
  - Time to target: `59.64s` at `3000`
- CLIP multi merge
  - Selected priors: `lamp_0085`, `sofa_0131`, `sofa_0195`, `chair_0016`
  - PSNR@7000: `13.3182`
  - Total optimization time: `148.96s`
  - Time to same target: `106.40s` at `5000`
- mean_rgb multi merge
  - Selected priors: `lamp_0019`, `sofa_0003`, `sofa_0003`, `chair_0201`
  - PSNR@7000: `13.3023`
  - Total optimization time: `148.27s`
  - Time to same target: `105.91s` at `5000`
- CLIP+geometry multi merge
  - Selected priors: `lamp_0085`, `sofa_0131`, `sofa_0114`, `chair_0016`
  - PSNR@7000: `13.3151`
  - SSIM@7000: `0.6262`
  - LPIPS@7000: `0.3043`
  - Total optimization time: `149.64s`
  - Time to same target: `106.89s` at `5000`
- CLIP+geometry multi weighted_merge
  - Selected priors: `lamp_0085`, `sofa_0131`, `sofa_0114`, `chair_0016`
  - Kept points:
    - `lamp_0085`: `15157 / 25400`
    - `sofa_0131`: `20505 / 27457`
    - `sofa_0114`: `6504 / 26015`
    - `chair_0016`: `28923 / 28923`
  - PSNR@7000: `13.3025`
  - SSIM@7000: `0.6253`
  - LPIPS@7000: `0.3070`
  - Total optimization time: `146.67s`
  - Time to same target: `104.76s` at `5000`
- CLIP+geometry multi filtered_merge
  - Selected priors: `lamp_0085`, `sofa_0131`, `sofa_0114`, `chair_0016`
  - Dropped priors: `lamp_0085`, `sofa_0114`
  - Kept priors: `sofa_0131`, `chair_0016`
  - PSNR@7000: `13.2884`
  - SSIM@7000: `0.6255`
  - LPIPS@7000: `0.3031`
  - Total optimization time: `145.44s`
  - Time to same target: `103.89s` at `5000`

### office_0

- Baseline multi
  - PSNR@7000: `12.9721`
  - SSIM@7000: `0.5606`
  - LPIPS@7000: `0.3631`
  - Total optimization time: `146.48s`
  - Baseline 3000-iter PSNR target: `12.4943`
  - Time to target: `62.78s` at `3000`
- CLIP multi merge
  - Selected priors: `sofa_0131`, `sofa_0131`, `table_0230`, `chair_0239`
  - PSNR@7000: `12.9827`
  - Total optimization time: `154.72s`
  - Time to same target: `66.31s` at `3000`
- mean_rgb multi merge
  - Selected priors: `sofa_0003`, `sofa_0050`, `table_0020`, `chair_0240`
  - PSNR@7000: `12.9568`
  - Total optimization time: `153.38s`
  - Time to same target: `65.73s` at `3000`
- CLIP+geometry multi merge
  - Selected priors: `sofa_0128`, `sofa_0065`, `table_0230`, `chair_0239`
  - PSNR@7000: `12.9392`
  - SSIM@7000: `0.5578`
  - LPIPS@7000: `0.3660`
  - Total optimization time: `153.68s`
  - Time to same target: `65.86s` at `3000`
- CLIP+geometry multi weighted_merge
  - Selected priors: `sofa_0128`, `sofa_0065`, `table_0230`, `chair_0239`
  - Kept points:
    - `sofa_0128`: `5926 / 23704`
    - `sofa_0065`: `9914 / 22689`
    - `table_0230`: `19833 / 19833`
    - `chair_0239`: `10911 / 22920`
  - PSNR@7000: `12.9882`
  - SSIM@7000: `0.5623`
  - LPIPS@7000: `0.3639`
  - Total optimization time: `150.00s`
  - Time to same target: `107.14s` at `5000`
- CLIP+geometry multi filtered_merge
  - Selected priors: `sofa_0128`, `sofa_0065`, `table_0230`, `chair_0239`
  - Dropped priors: `sofa_0128`, `sofa_0065`, `chair_0239`
  - Kept priors: `table_0230`
  - PSNR@7000: `12.9454`
  - SSIM@7000: `0.5593`
  - LPIPS@7000: `0.3654`
  - Total optimization time: `148.19s`
  - Time to same target: `105.85s` at `5000`

## Takeaways

- `CLIP+geometry` retrieval by itself did not improve convergence on Replica. In both scenes, plain `clip_geom merge` stayed slower than baseline and did not beat the earlier CLIP multi-object run.
- The insertion policy mattered more than the new retrieval feature.
- In `room_0`, `weighted_merge` and `filtered_merge` reduced total runtime relative to plain `clip_geom merge`, but both still needed `5000` iterations to reach the baseline `3000`-iteration PSNR target.
- In `office_0`, `weighted_merge` gave the best final PSNR among the `clip_geom` variants, but convergence slowed materially because the target PSNR was not reached until `5000` iterations.
- `filtered_merge` behaved like a strong selection ablation. For `office_0`, only `table_0230` survived filtering, and that still did not beat the vanilla baseline in speed or final quality.
- Under the current Replica setup, the main bottleneck still looks more like `prior usefulness during optimization` than simply `number of inserted priors`.

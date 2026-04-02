# Replica Multi-Object 15000-Iter Rerun with Initial Gaussian Snapshots

Date: 2026-03-18

## Setup

- Dataset: Replica scene-centric multi-object exports on shared SSD
- Scenes: `room_0`, `office_0`
- Experiments rerun:
  - `baseline_from_scratch_vanilla_3dgs_multi_15000`
  - `oracle_prior_vanilla_3dgs_multi_mean_rgb_15000`
  - `oracle_prior_vanilla_3dgs_multi_clip_15000`
  - `oracle_prior_vanilla_3dgs_multi_clip_geom_15000`
- Target selection: categories `chair`, `sofa`, `table`, `lamp` within each scene, top-4 objects by volume
- Prior insertion: oracle alignment + multi-prior `merge`
- Training schedule:
  - `iterations: 15000`
  - checkpoints: `500, 1000, 2000, 3000, 5000, 7000, 10000, 15000`
- Execution order: all eight runs executed sequentially to keep wall-clock comparisons fair

## Initial Snapshot Contract

- Every run now saves the exact pre-optimization Gaussian state after initialization.
- Canonical artifacts:
  - `point_cloud/iteration_0/point_cloud.ply`
  - `train/ours_0/renders/*.png`
  - `test/ours_0/renders/*.png`
- These are saved in each backend model directory and also referenced from `backend_run.json`.

## Method Note

- `mean_rgb` retrieval code was not replaced. It remains available for exact reproduction of earlier runs.
- `CLIP` and `CLIP+geometry` were rerun under the same multi-object setting to compare only the retrieval backend while keeping the same insertion rule.
- Working hypothesis only: part of the gap may still come from synthetic ShapeSplat priors versus Replica indoor scenes. That domain-gap idea is noted here for future follow-up on a CAD-based synthetic indoor dataset, but it is not treated as a variable in this report.

## Results

### room_0

- Baseline multi
  - Final metrics at `15000`
    - PSNR: `13.6677`
    - SSIM: `0.6604`
    - LPIPS: `0.2802`
    - Total optimization time: `422.05s`
  - Baseline `3000`-iter PSNR target: `12.8448`
  - Time to target: `84.41s`
  - Delta vs previous `7000` run: `+0.3586 PSNR`
  - Initial snapshot:
    - PLY: `outputs/backend_runs/baseline_from_scratch_vanilla_3dgs_multi_15000/room_0/point_cloud/iteration_0/point_cloud.ply`
    - Train renders: `outputs/backend_runs/baseline_from_scratch_vanilla_3dgs_multi_15000/room_0/train/ours_0/renders`
    - Test renders: `outputs/backend_runs/baseline_from_scratch_vanilla_3dgs_multi_15000/room_0/test/ours_0/renders`
- Mean-RGB multi prior
  - Selected priors: `lamp_0019`, `sofa_0003`, `sofa_0003`, `chair_0201`
  - Final metrics at `15000`
    - PSNR: `13.6662`
    - SSIM: `0.6629`
    - LPIPS: `0.2770`
    - Total optimization time: `433.13s`
  - Time to same target: `86.63s`
  - Delta vs previous `7000` run: `+0.3639 PSNR`
  - Delta vs baseline at `15000`: `-0.0015 PSNR`, `+0.0025 SSIM`, `-0.0033 LPIPS`
  - Initial snapshot:
    - PLY: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_mean_rgb_15000/room_0/point_cloud/iteration_0/point_cloud.ply`
    - Train renders: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_mean_rgb_15000/room_0/train/ours_0/renders`
    - Test renders: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_mean_rgb_15000/room_0/test/ours_0/renders`
- CLIP multi prior
  - Selected priors: `lamp_0085`, `sofa_0131`, `sofa_0195`, `chair_0016`
  - Final metrics at `15000`
    - PSNR: `13.7153`
    - SSIM: `0.6676`
    - LPIPS: `0.2751`
    - Total optimization time: `440.94s`
  - Time to same target: `88.19s`
  - Delta vs previous `7000` run: `+0.3971 PSNR`
  - Delta vs baseline at `15000`: `+0.0477 PSNR`, `+0.0071 SSIM`, `-0.0051 LPIPS`
  - Initial snapshot:
    - PLY: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_15000/room_0/point_cloud/iteration_0/point_cloud.ply`
    - Train renders: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_15000/room_0/train/ours_0/renders`
    - Test renders: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_15000/room_0/test/ours_0/renders`
- CLIP+geometry multi prior
  - Selected priors: `lamp_0085`, `sofa_0131`, `sofa_0114`, `chair_0016`
  - Final metrics at `15000`
    - PSNR: `13.6696`
    - SSIM: `0.6637`
    - LPIPS: `0.2773`
    - Total optimization time: `441.02s`
  - Time to same target: `88.20s`
  - Delta vs previous `7000` run: `+0.3545 PSNR`
  - Delta vs baseline at `15000`: `+0.0019 PSNR`, `+0.0032 SSIM`, `-0.0030 LPIPS`
  - Initial snapshot:
    - PLY: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_geom_15000/room_0/point_cloud/iteration_0/point_cloud.ply`
    - Train renders: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_geom_15000/room_0/train/ours_0/renders`
    - Test renders: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_geom_15000/room_0/test/ours_0/renders`

### office_0

- Baseline multi
  - Final metrics at `15000`
    - PSNR: `13.2911`
    - SSIM: `0.5942`
    - LPIPS: `0.3393`
    - Total optimization time: `448.44s`
  - Baseline `3000`-iter PSNR target: `12.4948`
  - Time to target: `89.69s`
  - Delta vs previous `7000` run: `+0.3190 PSNR`
  - Initial snapshot:
    - PLY: `outputs/backend_runs/baseline_from_scratch_vanilla_3dgs_multi_15000/office_0/point_cloud/iteration_0/point_cloud.ply`
    - Train renders: `outputs/backend_runs/baseline_from_scratch_vanilla_3dgs_multi_15000/office_0/train/ours_0/renders`
    - Test renders: `outputs/backend_runs/baseline_from_scratch_vanilla_3dgs_multi_15000/office_0/test/ours_0/renders`
- Mean-RGB multi prior
  - Selected priors: `sofa_0003`, `sofa_0050`, `table_0020`, `chair_0240`
  - Final metrics at `15000`
    - PSNR: `13.2855`
    - SSIM: `0.5934`
    - LPIPS: `0.3407`
    - Total optimization time: `458.71s`
  - Time to same target: `91.74s`
  - Delta vs previous `7000` run: `+0.3287 PSNR`
  - Delta vs baseline at `15000`: `-0.0055 PSNR`, `-0.0008 SSIM`, `+0.0014 LPIPS`
  - Initial snapshot:
    - PLY: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_mean_rgb_15000/office_0/point_cloud/iteration_0/point_cloud.ply`
    - Train renders: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_mean_rgb_15000/office_0/train/ours_0/renders`
    - Test renders: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_mean_rgb_15000/office_0/test/ours_0/renders`
- CLIP multi prior
  - Selected priors: `sofa_0131`, `sofa_0131`, `table_0230`, `chair_0239`
  - Final metrics at `15000`
    - PSNR: `13.3070`
    - SSIM: `0.5958`
    - LPIPS: `0.3385`
    - Total optimization time: `460.03s`
  - Time to same target: `153.34s`
  - Delta vs previous `7000` run: `+0.3243 PSNR`
  - Delta vs baseline at `15000`: `+0.0159 PSNR`, `+0.0015 SSIM`, `-0.0008 LPIPS`
  - Initial snapshot:
    - PLY: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_15000/office_0/point_cloud/iteration_0/point_cloud.ply`
    - Train renders: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_15000/office_0/train/ours_0/renders`
    - Test renders: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_15000/office_0/test/ours_0/renders`
- CLIP+geometry multi prior
  - Selected priors: `sofa_0128`, `sofa_0065`, `table_0230`, `chair_0239`
  - Final metrics at `15000`
    - PSNR: `13.3037`
    - SSIM: `0.5943`
    - LPIPS: `0.3396`
    - Total optimization time: `460.12s`
  - Time to same target: `153.37s`
  - Delta vs previous `7000` run: `+0.3644 PSNR`
  - Delta vs baseline at `15000`: `+0.0126 PSNR`, `+0.0001 SSIM`, `+0.0003 LPIPS`
  - Initial snapshot:
    - PLY: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_geom_15000/office_0/point_cloud/iteration_0/point_cloud.ply`
    - Train renders: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_geom_15000/office_0/train/ours_0/renders`
    - Test renders: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_geom_15000/office_0/test/ours_0/renders`

## Takeaways

- Extending the horizon from `7000` to `15000` improved all four experiment families in both scenes. The gain was about `+0.32` to `+0.40` PSNR over the previous `7000` runs.
- `room_0` at `15000` favored `CLIP` retrieval. It gave the best final PSNR, SSIM, and LPIPS among the four runs, but it still reached the baseline `3000`-iteration target later than vanilla.
- `office_0` at `15000` also favored `CLIP` retrieval on final quality, but the convergence delay remained severe. Both `CLIP` and `CLIP+geometry` needed about `153s` to match the baseline `3000`-iteration PSNR target, versus `89.69s` for baseline.
- `mean_rgb` remained reproducible and available, but it did not overtake `CLIP` at `15000` in either scene.
- Saving `iteration_0` and `ours_0` makes the initial condition difference directly inspectable now. This should help separate “bad retrieval” from “optimization disturbance after insertion” in the next round.

## Reference Outputs

- Summary table: `outputs/reports/summary.md`
- Summary CSV: `outputs/reports/summary.csv`
- Checkpoint CSV: `outputs/reports/checkpoints.csv`

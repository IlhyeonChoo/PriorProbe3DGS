# Replica Single-Object CLIP Oracle vs Vanilla 3DGS

Date: 2026-03-17

## Setup

- Dataset: Replica target-centric single-object exports on shared SSD
- Scenes: `room_0`, `office_0`
- Target selection: `chair` category, maximum-volume object per scene
- Prior library: ShapeSplat ModelNet chair subset, `256` objects
- Retrieval feature: `open_clip` `ViT-B-32` / `laion2b_s34b_b79k`
- Fallback: disabled
- Reconstruction backend: vanilla 3DGS
- Insertion mode: oracle alignment + single-prior `merge` init
- Baseline: existing `baseline_from_scratch_vanilla_3dgs`
- Note: the two CLIP oracle runs were launched concurrently, so their wall-clock times should not be treated as a clean speed comparison against the earlier sequential baseline/mean-RGB runs.
- Mean-RGB single-object baseline/oracle reference:
  [replica_single_object_mean_rgb_baseline_vs_oracle_2026-03-17.md](/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS/docs/experiments/replica_single_object_mean_rgb_baseline_vs_oracle_2026-03-17.md)

## Results

### room_0

- Vanilla baseline
  - PSNR@7000: `13.0644`
  - SSIM@7000: `0.4940`
  - LPIPS@7000: `0.4027`
  - Total optimization time: `118.72s`
- Oracle prior with CLIP retrieval
  - Selected prior: `chair_0014`
  - Retrieval score: `0.7662`
  - PSNR@7000: `13.0660`
  - SSIM@7000: `0.4984`
  - LPIPS@7000: `0.4019`
  - Total optimization time: `238.93s`
- Mean-RGB oracle reference
  - Selected prior: `chair_0201`
  - Retrieval score: `0.9986`
  - PSNR@7000: `13.0911`
  - SSIM@7000: `0.4968`
  - LPIPS@7000: `0.4005`
  - Total optimization time: `121.31s`

### office_0

- Vanilla baseline
  - PSNR@7000: `12.6235`
  - SSIM@7000: `0.4569`
  - LPIPS@7000: `0.4583`
  - Total optimization time: `133.93s`
- Oracle prior with CLIP retrieval
  - Selected prior: `chair_0014`
  - Retrieval score: `0.7022`
  - PSNR@7000: `12.6547`
  - SSIM@7000: `0.4604`
  - LPIPS@7000: `0.4539`
  - Total optimization time: `257.22s`
- Mean-RGB oracle reference
  - Selected prior: `chair_0240`
  - Retrieval score: `0.9918`
  - PSNR@7000: `12.6543`
  - SSIM@7000: `0.4583`
  - LPIPS@7000: `0.4551`
  - Total optimization time: `136.43s`

## Takeaways

- Current CLIP single-object retrieval did not improve over the existing mean-RGB single-object oracle baseline.
- `office_0` final quality was marginally better than vanilla, but comparable to the earlier mean-RGB oracle run.
- `room_0` final quality was effectively flat relative to vanilla and weaker than the mean-RGB oracle run.
- In both scenes, the CLIP oracle run took substantially longer wall-clock time than the existing baseline runs.
- This strengthened the case for the next step: multi-object prior insertion, since a single inserted object may be too local and can underdeliver even with a stronger feature backend.

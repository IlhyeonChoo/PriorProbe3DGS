# Replica Gaussian-Direct Upper Bound

## Assumptions

- Prior insertion uses `gaussian_direct` rather than point-cloud proxy conversion.
- Alignment is fixed to `oracle_target_box` for all prior-based runs.
- `same_scene_exact` and `merged_oracle_select` are upper-bound settings, not generalization settings.
- Target PSNR is derived from `gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_diverse_384_15000` at iteration 3000, or the nearest earlier checkpoint when that iteration is absent.

## Dataset

- Dense dataset root: `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_diverse_384`
- Views per scene: `320 train + 64 test = 384`
- Selection mode: `diverse_azimuth`
- `room_0` azimuth histogram: `48, 49, 48, 48, 48, 48, 48, 47`
- `office_0` azimuth histogram: `48, 48, 48, 48, 48, 48, 48, 48`

## Target Quality Thresholds

| scene | target_psnr | reference_iteration |
|---|---:|---:|
| room_0 | 10.628532 | 3000 |
| office_0 | 11.130353 | 3000 |

## Results

| experiment | scene | target_psnr | time_to_target_sec | total_time_sec | psnr | ssim | lpips | prior_count | initial_gaussians | inserted_gaussians | exact_match_rate | same_scene_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_diverse_384_15000 | room_0 | 10.628532 | 118.847082 | 594.2354075768963 | 12.487881660461426 | 0.5459524393081665 | 0.3359781801700592 | 0 | 100000 | None | n/a | n/a |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_diverse_384_15000 | office_0 | 11.130353 | 144.412072 | 722.0603584530763 | 12.951544761657715 | 0.5773675441741943 | 0.3179364502429962 | 0 | 100000 | None | n/a | n/a |
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | room_0 | 10.628532 | 124.032383 | 620.1619126070291 | 12.43500804901123 | 0.53803551197052 | 0.3492640554904938 | 4 | 200000 | 100000 | 1.000 | 1.000 |
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | office_0 | 11.130353 | 150.958467 | 754.7923339707777 | 12.976933479309082 | 0.5890350341796875 | 0.30406665802001953 | 4 | 200000 | 100000 | 1.000 | 1.000 |

## Retrieval Provenance

| experiment | scene | target_object | target_category | selected_prior | selected_category | score | exact_match | same_scene_match | asset_format |
|---|---|---:|---|---|---|---:|---|---|---|
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | room_0 | 6 | lamp | replica_room_0_obj_6 | lamp | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | room_0 | 9 | sofa | replica_room_0_obj_9 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | room_0 | 77 | sofa | replica_room_0_obj_77 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | room_0 | 74 | chair | replica_room_0_obj_74 | chair | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | office_0 | 9 | sofa | replica_office_0_obj_9 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | office_0 | 7 | sofa | replica_office_0_obj_7 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | office_0 | 58 | table | replica_office_0_obj_58 | table | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | office_0 | 61 | chair | replica_office_0_obj_61 | chair | 1.0 | True | True | gaussian |

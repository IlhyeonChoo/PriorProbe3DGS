# Replica Gaussian-Direct Phase 1 Protection Sweep

- 기준 iteration: baseline `3000` checkpoint PSNR
- 비교 범위: 96-view same-scene exact vs dense 384 same-scene exact
- protection 비교: `none`, `weak(0.02)`, `freeze`

## 96-view

| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000 | room_0 | none | 12.851452 | 84.353029 | 421.7651470587589 | 13.653732299804688 | 0.660018265247345 | 0.2825828790664673 | 100000 | 1166507 | 2571919 | n/a | n/a |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000 | office_0 | none | 12.490562 | 89.547757 | 447.7387832701206 | 13.303287506103516 | 0.5935389399528503 | 0.3406592905521393 | 100000 | 1212339 | 2706134 | n/a | n/a |
| gaussian_direct_same_scene_exact_clip_15000 | room_0 | none | 12.851452 | 90.956868 | 454.78434128919616 | 13.741816520690918 | 0.6699320673942566 | 0.27153480052948 | 200000 | 1325595 | 2706795 | n/a | n/a |
| gaussian_direct_same_scene_exact_clip_15000 | office_0 | none | 12.490562 | 65.708953 | 492.817148336675 | 13.680407524108887 | 0.6440250873565674 | 0.2907118797302246 | 200000 | 1429553 | 2910198 | n/a | n/a |
| gaussian_direct_same_scene_exact_clip_weak_15000 | room_0 | weak(0.02) | 12.851452 | 81.766100 | 408.83049751026556 | 13.722380638122559 | 0.6658915877342224 | 0.27292686700820923 | 200000 | 1101463 | 2298034 | 100000 | 100000 |
| gaussian_direct_same_scene_exact_clip_weak_15000 | office_0 | weak(0.02) | 12.490562 | 52.612761 | 394.59570517530665 | 13.579524993896484 | 0.6257382035255432 | 0.3034648001194 | 200000 | 1134144 | 2180482 | 100000 | 100000 |

## Dense 384-view

| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_diverse_384_15000 | room_0 | none | 10.628532 | 118.847082 | 594.2354075768963 | 12.487881660461426 | 0.5459524393081665 | 0.3359781801700592 | 100000 | 1152886 | 3916981 | n/a | n/a |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_diverse_384_15000 | office_0 | none | 11.130353 | 144.412072 | 722.0603584530763 | 12.951544761657715 | 0.5773675441741943 | 0.3179364502429962 | 100000 | 1395688 | 4795606 | n/a | n/a |
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | room_0 | none | 10.628532 | 124.032383 | 620.1619126070291 | 12.43500804901123 | 0.53803551197052 | 0.3492640554904938 | 200000 | 1291896 | 4042500 | n/a | n/a |
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | office_0 | none | 11.130353 | 150.958467 | 754.7923339707777 | 12.976933479309082 | 0.5890350341796875 | 0.30406665802001953 | 200000 | 1541066 | 4926541 | n/a | n/a |
| gaussian_direct_same_scene_exact_clip_diverse_384_weak_15000 | room_0 | weak(0.02) | 10.628532 | 112.027473 | 560.1373671968468 | 12.374943733215332 | 0.5295525789260864 | 0.3520362079143524 | 200000 | 1136436 | 3549813 | 100000 | 100000 |
| gaussian_direct_same_scene_exact_clip_diverse_384_weak_15000 | office_0 | weak(0.02) | 11.130353 | 138.395447 | 691.9772328911349 | 12.838061332702637 | 0.5537205934524536 | 0.3350534439086914 | 200000 | 1395379 | 4342981 | 100000 | 100000 |
| gaussian_direct_same_scene_exact_clip_diverse_384_freeze_15000 | room_0 | freeze | 10.628532 | 183.707660 | 551.1229802109301 | 11.858847618103027 | 0.4844341278076172 | 0.39541366696357727 | 200000 | 1097890 | 3414144 | 100000 | 100000 |
| gaussian_direct_same_scene_exact_clip_diverse_384_freeze_15000 | office_0 | freeze | 11.130353 | 317.770002 | 680.9357189396396 | 11.67116641998291 | 0.4145631790161133 | 0.47279059886932373 | 200000 | 1359424 | 4225775 | 100000 | 100000 |

## Artifacts

- Summary CSV: `../../outputs/gaussian_direct/reports/replica_gaussian_direct_protection_phase1_summary.csv`
- Checkpoint CSV: `../../outputs/gaussian_direct/reports/replica_gaussian_direct_protection_phase1_checkpoints.csv`

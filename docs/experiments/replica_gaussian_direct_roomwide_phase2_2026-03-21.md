# Replica Gaussian-Direct Phase 2 Legacy Biased Room-Wide Views

- 이 문서는 현재 `legacy_biased_roomwide_384` 결과를 기록한 문서다.
- 이후 `roomwide_v2_*`는 별도 exporter와 별도 보고서로 비교한다.

- 기준 iteration: family baseline `3000` checkpoint PSNR
- 비교 범위: object-centric dense 384-view vs room-wide 384-view
- protection 비교: `none`, `weak(0.02)`

## Object-Centric Dense 384

| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 | target_visible_min | target_visible_max |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_diverse_384_15000 | room_0 | none | 10.628532 | 118.847082 | 594.2354075768963 | 12.487881660461426 | 0.5459524393081665 | 0.3359781801700592 | 100000 | 1152886 | 3916981 | n/a | n/a | 144 | 384 |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_diverse_384_15000 | office_0 | none | 11.130353 | 144.412072 | 722.0603584530763 | 12.951544761657715 | 0.5773675441741943 | 0.3179364502429962 | 100000 | 1395688 | 4795606 | n/a | n/a | 384 | 384 |
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | room_0 | none | 10.628532 | 124.032383 | 620.1619126070291 | 12.43500804901123 | 0.53803551197052 | 0.3492640554904938 | 200000 | 1291896 | 4042500 | n/a | n/a | 144 | 384 |
| gaussian_direct_same_scene_exact_clip_diverse_384_15000 | office_0 | none | 11.130353 | 150.958467 | 754.7923339707777 | 12.976933479309082 | 0.5890350341796875 | 0.30406665802001953 | 200000 | 1541066 | 4926541 | n/a | n/a | 384 | 384 |
| gaussian_direct_same_scene_exact_clip_diverse_384_weak_15000 | room_0 | weak(0.02) | 10.628532 | 112.027473 | 560.1373671968468 | 12.374943733215332 | 0.5295525789260864 | 0.3520362079143524 | 200000 | 1136436 | 3549813 | 100000 | 100000 | 144 | 384 |
| gaussian_direct_same_scene_exact_clip_diverse_384_weak_15000 | office_0 | weak(0.02) | 11.130353 | 138.395447 | 691.9772328911349 | 12.838061332702637 | 0.5537205934524536 | 0.3350534439086914 | 200000 | 1395379 | 4342981 | 100000 | 100000 | 384 | 384 |

## Room-Wide 384

| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 | target_visible_min | target_visible_max |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_384_15000 | room_0 | none | 10.568237 | 160.942096 | 804.7104814262129 | 12.28219223022461 | 0.618870198726654 | 0.2949766218662262 | 100000 | 1321531 | 5519919 | n/a | n/a | 158 | 384 |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_384_15000 | office_0 | none | 10.173265 | 178.470948 | 892.3547409600578 | 12.08999252319336 | 0.609119713306427 | 0.31194618344306946 | 100000 | 1479462 | 6460656 | n/a | n/a | 124 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_384_15000 | room_0 | none | 10.568237 | 168.557215 | 842.7860753959976 | 12.325146675109863 | 0.6206886172294617 | 0.29368001222610474 | 200000 | 1464170 | 5686544 | 99243 | 74441 | 158 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_384_15000 | office_0 | none | 10.173265 | 187.978705 | 939.8935252879746 | 12.30894947052002 | 0.625828742980957 | 0.2971493899822235 | 200000 | 1636817 | 6850703 | 99172 | 71026 | 124 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_384_weak_15000 | room_0 | weak(0.02) | 10.568237 | 162.927219 | 814.6360936318524 | 12.244332313537598 | 0.6135476231575012 | 0.2995116710662842 | 200000 | 1325831 | 5228865 | 100000 | 100000 | 158 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_384_weak_15000 | office_0 | weak(0.02) | 10.173265 | 183.540522 | 917.7026084912941 | 12.183032035827637 | 0.6204885244369507 | 0.30146661400794983 | 200000 | 1558255 | 6401951 | 100000 | 100000 | 124 | 384 |

## Artifact

- Summary CSV: `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/reports/replica_gaussian_direct_roomwide_phase2_summary.csv`

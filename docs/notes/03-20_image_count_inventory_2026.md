# Replica Image Count Inventory

- 목적: 현재 gaussian-direct 실험 결과를 reconstruction 입력 이미지 수 기준으로 정리한다.
- 기준: `outputs/gaussian_direct/experiments/**/backend_run.json`를 스캔하고, 각 run의 `source_path/images` 실제 파일 수를 센다.

## Summary

- total runs: `70`
- groups: `3`

## 96 images

- source root: `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi`
- run count: `60`
- scenes: `office_0, office_0_backup_20260318_171856, office_0_backup_20260318_172813, office_0_backup_20260319_012052, office_0_backup_20260319_013014, room_0, room_0_backup_20260318_132328, room_0_backup_20260320_124631, room_0_backup_20260320_130338, room_0_backup_20260320_132205, room_0_backup_20260320_134031`
- splits: `? train / ? test`

| Experiment | Scene | Iterations | Backup | Run Dir |
| --- | --- | ---: | --- | --- |
| `baseline_from_scratch_vanilla_3dgs_multi` | `office_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/baseline_from_scratch_vanilla_3dgs_multi/office_0` |
| `baseline_from_scratch_vanilla_3dgs_multi` | `room_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/baseline_from_scratch_vanilla_3dgs_multi/room_0` |
| `baseline_from_scratch_vanilla_3dgs_multi_15000` | `office_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/baseline_from_scratch_vanilla_3dgs_multi_15000/office_0` |
| `baseline_from_scratch_vanilla_3dgs_multi_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/baseline_from_scratch_vanilla_3dgs_multi_15000/room_0` |
| `baseline_from_scratch_vanilla_3dgs_multi_15000` | `room_0_backup_20260318_132328` | `15000` | `yes` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/baseline_from_scratch_vanilla_3dgs_multi_15000/room_0_backup_20260318_132328` |
| `gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000` | `office_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000/office_0` |
| `gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000/room_0` |
| `gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000` | `room_0_backup_20260320_124631` | `15000` | `yes` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000/room_0_backup_20260320_124631` |
| `gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_smoke_1000` | `office_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_smoke_1000/office_0` |
| `gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_smoke_1000` | `room_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_smoke_1000/room_0` |
| `gaussian_direct_existing_clip_only_15000` | `office_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_existing_clip_only_15000/office_0` |
| `gaussian_direct_existing_clip_only_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_existing_clip_only_15000/room_0` |
| `gaussian_direct_existing_clip_only_smoke_1000` | `office_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_existing_clip_only_smoke_1000/office_0` |
| `gaussian_direct_existing_clip_only_smoke_1000` | `room_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_existing_clip_only_smoke_1000/room_0` |
| `gaussian_direct_merged_clip_retrieval_15000` | `office_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_merged_clip_retrieval_15000/office_0` |
| `gaussian_direct_merged_clip_retrieval_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_merged_clip_retrieval_15000/room_0` |
| `gaussian_direct_merged_clip_retrieval_15000` | `room_0_backup_20260320_134031` | `15000` | `yes` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_merged_clip_retrieval_15000/room_0_backup_20260320_134031` |
| `gaussian_direct_merged_clip_retrieval_smoke_1000` | `office_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_merged_clip_retrieval_smoke_1000/office_0` |
| `gaussian_direct_merged_clip_retrieval_smoke_1000` | `room_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_merged_clip_retrieval_smoke_1000/room_0` |
| `gaussian_direct_merged_oracle_select_clip_15000` | `office_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_merged_oracle_select_clip_15000/office_0` |
| `gaussian_direct_merged_oracle_select_clip_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_merged_oracle_select_clip_15000/room_0` |
| `gaussian_direct_merged_oracle_select_clip_15000` | `room_0_backup_20260320_132205` | `15000` | `yes` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_merged_oracle_select_clip_15000/room_0_backup_20260320_132205` |
| `gaussian_direct_merged_oracle_select_clip_smoke_1000` | `office_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_merged_oracle_select_clip_smoke_1000/office_0` |
| `gaussian_direct_merged_oracle_select_clip_smoke_1000` | `room_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_merged_oracle_select_clip_smoke_1000/room_0` |
| `gaussian_direct_oracle_prior_vanilla_3dgs_multi_clip_smoke_1000` | `room_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_oracle_prior_vanilla_3dgs_multi_clip_smoke_1000/room_0` |
| `gaussian_direct_oracle_prior_vanilla_3dgs_multi_mean_rgb_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_oracle_prior_vanilla_3dgs_multi_mean_rgb_15000/room_0` |
| `gaussian_direct_oracle_prior_vanilla_3dgs_single_clip_replace_smoke_1000` | `room_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_oracle_prior_vanilla_3dgs_single_clip_replace_smoke_1000/room_0` |
| `gaussian_direct_same_scene_exact_clip_15000` | `office_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_same_scene_exact_clip_15000/office_0` |
| `gaussian_direct_same_scene_exact_clip_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_same_scene_exact_clip_15000/room_0` |
| `gaussian_direct_same_scene_exact_clip_15000` | `room_0_backup_20260320_130338` | `15000` | `yes` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_same_scene_exact_clip_15000/room_0_backup_20260320_130338` |
| `gaussian_direct_same_scene_exact_clip_smoke_1000` | `office_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_same_scene_exact_clip_smoke_1000/office_0` |
| `gaussian_direct_same_scene_exact_clip_smoke_1000` | `room_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/gaussian_direct_same_scene_exact_clip_smoke_1000/room_0` |
| `oracle_prior_vanilla_3dgs_multi_clip` | `office_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip/office_0` |
| `oracle_prior_vanilla_3dgs_multi_clip` | `room_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip/room_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_15000` | `office_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_15000/office_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_15000/room_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_alignfix_v1_15000` | `office_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_alignfix_v1_15000/office_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_alignfix_v1_15000` | `office_0_backup_20260318_171856` | `15000` | `yes` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_alignfix_v1_15000/office_0_backup_20260318_171856` |
| `oracle_prior_vanilla_3dgs_multi_clip_alignfix_v1_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_alignfix_v1_15000/room_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_alignfix_v2_15000` | `office_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_alignfix_v2_15000/office_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_alignfix_v2_15000` | `office_0_backup_20260318_172813` | `15000` | `yes` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_alignfix_v2_15000/office_0_backup_20260318_172813` |
| `oracle_prior_vanilla_3dgs_multi_clip_alignfix_v2_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_alignfix_v2_15000/room_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_geom` | `office_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_geom/office_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_geom` | `room_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_geom/room_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_geom_15000` | `office_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_geom_15000/office_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_geom_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_geom_15000/room_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_geom_filtered` | `office_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_geom_filtered/office_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_geom_filtered` | `room_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_geom_filtered/room_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_geom_weighted` | `office_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_geom_weighted/office_0` |
| `oracle_prior_vanilla_3dgs_multi_clip_geom_weighted` | `room_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_clip_geom_weighted/room_0` |
| `oracle_prior_vanilla_3dgs_multi_mean_rgb` | `office_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_mean_rgb/office_0` |
| `oracle_prior_vanilla_3dgs_multi_mean_rgb` | `room_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_mean_rgb/room_0` |
| `oracle_prior_vanilla_3dgs_multi_mean_rgb_15000` | `office_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_mean_rgb_15000/office_0` |
| `oracle_prior_vanilla_3dgs_multi_mean_rgb_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_mean_rgb_15000/room_0` |
| `oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v1_15000` | `office_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v1_15000/office_0` |
| `oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v1_15000` | `office_0_backup_20260319_012052` | `15000` | `yes` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v1_15000/office_0_backup_20260319_012052` |
| `oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v1_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v1_15000/room_0` |
| `oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v2_15000` | `office_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v2_15000/office_0` |
| `oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v2_15000` | `office_0_backup_20260319_013014` | `15000` | `yes` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v2_15000/office_0_backup_20260319_013014` |
| `oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v2_15000` | `room_0` | `15000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_multi_mean_rgb_alignfix_v2_15000/room_0` |

## 97 images

- source root: `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS/data/public_datasets/replica_colmap`
- run count: `3`
- scenes: `office_0, room_0`
- splits: `? train / ? test`

| Experiment | Scene | Iterations | Backup | Run Dir |
| --- | --- | ---: | --- | --- |
| `baseline_from_scratch_vanilla_3dgs` | `office_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/baseline_from_scratch_vanilla_3dgs` |
| `baseline_smoke_vanilla_3dgs` | `room_0` | `1` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/baseline_smoke_vanilla_3dgs/room_0` |
| `oracle_prior_vanilla_3dgs` | `office_0` | `1000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs` |

## 97 images

- source root: `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap`
- run count: `7`
- scenes: `office_0, room_0`
- splits: `? train / ? test`

| Experiment | Scene | Iterations | Backup | Run Dir |
| --- | --- | ---: | --- | --- |
| `baseline_from_scratch_vanilla_3dgs` | `office_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/baseline_from_scratch_vanilla_3dgs/office_0` |
| `baseline_from_scratch_vanilla_3dgs` | `room_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/baseline_from_scratch_vanilla_3dgs/room_0` |
| `baseline_smoke_vanilla_3dgs` | `office_0` | `1` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/baseline_smoke_vanilla_3dgs/office_0` |
| `oracle_prior_vanilla_3dgs` | `office_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs/office_0` |
| `oracle_prior_vanilla_3dgs` | `room_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs/room_0` |
| `oracle_prior_vanilla_3dgs_clip` | `office_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_clip/office_0` |
| `oracle_prior_vanilla_3dgs_clip` | `room_0` | `7000` | `no` | `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/experiments/oracle_prior_vanilla_3dgs_clip/room_0` |

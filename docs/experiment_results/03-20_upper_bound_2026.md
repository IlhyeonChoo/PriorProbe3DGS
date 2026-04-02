# Replica Gaussian-Direct Upper Bound

## Assumptions

- Prior insertion uses `gaussian_direct` rather than point-cloud proxy conversion.
- Alignment is fixed to `oracle_target_box` for all prior-based runs.
- `same_scene_exact` and `merged_oracle_select` are upper-bound settings, not generalization settings.
- Target PSNR is derived from `gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000` at iteration 3000, or the nearest earlier checkpoint when that iteration is absent.

## Target Quality Thresholds

| scene | target_psnr | reference_iteration |
|---|---:|---:|
| room_0 | 12.851452 | 3000 |
| office_0 | 12.490562 | 3000 |

## Results

| experiment | scene | target_psnr | time_to_target_sec | total_time_sec | psnr | ssim | lpips | prior_count | initial_gaussians | inserted_gaussians | exact_match_rate | same_scene_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000 | room_0 | 12.851452 | 84.353029 | 421.7651470587589 | 13.653732299804688 | 0.660018265247345 | 0.2825828790664673 | 0 | 100000 | None | n/a | n/a |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_15000 | office_0 | 12.490562 | 89.547757 | 447.7387832701206 | 13.303287506103516 | 0.5935389399528503 | 0.3406592905521393 | 0 | 100000 | None | n/a | n/a |
| gaussian_direct_same_scene_exact_clip_15000 | room_0 | 12.851452 | 90.956868 | 454.78434128919616 | 13.741816520690918 | 0.6699320673942566 | 0.27153480052948 | 4 | 200000 | 100000 | 1.000 | 1.000 |
| gaussian_direct_same_scene_exact_clip_15000 | office_0 | 12.490562 | 65.708953 | 492.817148336675 | 13.680407524108887 | 0.6440250873565674 | 0.2907118797302246 | 4 | 200000 | 100000 | 1.000 | 1.000 |
| gaussian_direct_merged_oracle_select_clip_15000 | room_0 | 12.851452 | 90.826495 | 454.1324767349288 | 13.720746040344238 | 0.6659699082374573 | 0.2767050564289093 | 4 | 200000 | 100000 | 1.000 | 1.000 |
| gaussian_direct_merged_oracle_select_clip_15000 | office_0 | 12.490562 | 65.539656 | 491.54742096783593 | 13.672581672668457 | 0.6429884433746338 | 0.2899191677570343 | 4 | 200000 | 100000 | 1.000 | 1.000 |
| gaussian_direct_merged_clip_retrieval_15000 | room_0 | 12.851452 | 90.786349 | 453.93174515105784 | 13.738282203674316 | 0.6698997020721436 | 0.27215221524238586 | 4 | 200000 | 100000 | 1.000 | 1.000 |
| gaussian_direct_merged_clip_retrieval_15000 | office_0 | 12.490562 | 65.987350 | 494.9051231867634 | 13.69286060333252 | 0.6451852917671204 | 0.291142076253891 | 4 | 200000 | 100000 | 1.000 | 1.000 |
| gaussian_direct_existing_clip_only_15000 | room_0 | 12.851452 | 90.676352 | 453.38175852783024 | 13.7056303024292 | 0.6671122908592224 | 0.27269142866134644 | 4 | 203984 | 103984 | 0.000 | 0.000 |
| gaussian_direct_existing_clip_only_15000 | office_0 | 12.490562 | 160.741692 | 482.2250746320933 | 13.364607810974121 | 0.6072173714637756 | 0.330143541097641 | 4 | 197667 | 97667 | 0.000 | 0.000 |

## Retrieval Provenance

| experiment | scene | target_object | target_category | selected_prior | selected_category | score | exact_match | same_scene_match | asset_format |
|---|---|---:|---|---|---|---:|---|---|---|
| gaussian_direct_same_scene_exact_clip_15000 | room_0 | 6 | lamp | replica_room_0_obj_6 | lamp | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_15000 | room_0 | 9 | sofa | replica_room_0_obj_9 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_15000 | room_0 | 77 | sofa | replica_room_0_obj_77 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_15000 | room_0 | 74 | chair | replica_room_0_obj_74 | chair | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_15000 | office_0 | 9 | sofa | replica_office_0_obj_9 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_15000 | office_0 | 7 | sofa | replica_office_0_obj_7 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_15000 | office_0 | 58 | table | replica_office_0_obj_58 | table | 1.0 | True | True | gaussian |
| gaussian_direct_same_scene_exact_clip_15000 | office_0 | 61 | chair | replica_office_0_obj_61 | chair | 1.0 | True | True | gaussian |
| gaussian_direct_merged_oracle_select_clip_15000 | room_0 | 6 | lamp | replica_room_0_obj_6 | lamp | 1.0 | True | True | gaussian |
| gaussian_direct_merged_oracle_select_clip_15000 | room_0 | 9 | sofa | replica_room_0_obj_9 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_merged_oracle_select_clip_15000 | room_0 | 77 | sofa | replica_room_0_obj_77 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_merged_oracle_select_clip_15000 | room_0 | 74 | chair | replica_room_0_obj_74 | chair | 1.0 | True | True | gaussian |
| gaussian_direct_merged_oracle_select_clip_15000 | office_0 | 9 | sofa | replica_office_0_obj_9 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_merged_oracle_select_clip_15000 | office_0 | 7 | sofa | replica_office_0_obj_7 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_merged_oracle_select_clip_15000 | office_0 | 58 | table | replica_office_0_obj_58 | table | 1.0 | True | True | gaussian |
| gaussian_direct_merged_oracle_select_clip_15000 | office_0 | 61 | chair | replica_office_0_obj_61 | chair | 1.0 | True | True | gaussian |
| gaussian_direct_merged_clip_retrieval_15000 | room_0 | 6 | lamp | replica_room_0_obj_6 | lamp | 1.0 | True | True | gaussian |
| gaussian_direct_merged_clip_retrieval_15000 | room_0 | 9 | sofa | replica_room_0_obj_9 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_merged_clip_retrieval_15000 | room_0 | 77 | sofa | replica_room_0_obj_77 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_merged_clip_retrieval_15000 | room_0 | 74 | chair | replica_room_0_obj_74 | chair | 1.0 | True | True | gaussian |
| gaussian_direct_merged_clip_retrieval_15000 | office_0 | 9 | sofa | replica_office_0_obj_9 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_merged_clip_retrieval_15000 | office_0 | 7 | sofa | replica_office_0_obj_7 | sofa | 1.0 | True | True | gaussian |
| gaussian_direct_merged_clip_retrieval_15000 | office_0 | 58 | table | replica_office_0_obj_58 | table | 1.0 | True | True | gaussian |
| gaussian_direct_merged_clip_retrieval_15000 | office_0 | 61 | chair | replica_office_0_obj_61 | chair | 1.0 | True | True | gaussian |
| gaussian_direct_existing_clip_only_15000 | room_0 | 6 | lamp | lamp_0085 | lamp | 0.7352321743965149 | False | False | gaussian |
| gaussian_direct_existing_clip_only_15000 | room_0 | 9 | sofa | sofa_0131 | sofa | 0.7350780367851257 | False | False | gaussian |
| gaussian_direct_existing_clip_only_15000 | room_0 | 77 | sofa | sofa_0195 | sofa | 0.6666622757911682 | False | False | gaussian |
| gaussian_direct_existing_clip_only_15000 | room_0 | 74 | chair | chair_0016 | chair | 0.7506018877029419 | False | False | gaussian |
| gaussian_direct_existing_clip_only_15000 | office_0 | 9 | sofa | sofa_0131 | sofa | 0.6894411444664001 | False | False | gaussian |
| gaussian_direct_existing_clip_only_15000 | office_0 | 7 | sofa | sofa_0131 | sofa | 0.7218553423881531 | False | False | gaussian |
| gaussian_direct_existing_clip_only_15000 | office_0 | 58 | table | table_0230 | table | 0.8114539980888367 | False | False | gaussian |
| gaussian_direct_existing_clip_only_15000 | office_0 | 61 | chair | chair_0239 | chair | 0.7101907730102539 | False | False | gaussian |

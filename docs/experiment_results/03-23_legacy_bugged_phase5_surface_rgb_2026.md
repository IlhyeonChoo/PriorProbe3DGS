# Replica Gaussian-Direct Phase 5 Surface RGB

- Date: 2026-03-23
- Dataset family: `surface_rgb_roomwide_v2_384`
- Scenes: `room_0`, `office_0`
- 비교 기준: absolute PSNR/SSIM/LPIPS와 scene별 baseline 대비 delta

## Summary

| scene | label | iter_0_psnr | iter_3000_psnr | final_psnr | final_delta_vs_baseline | total_time_sec | ttt_sec | prior_inserted_total | survived@15000 | survival@15000 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| room_0 | baseline | 11.2341 | 41.6301 | 46.6816 | n/a | 160.07 | 32.01 | 0 | n/a | n/a |
| office_0 | baseline | 13.0536 | 36.5802 | 43.7367 | n/a | 158.45 | 31.69 | 0 | n/a | n/a |
| room_0 | prior_full | 11.2175 | 42.7781 | 47.1955 | 0.5138 | 183.59 | 36.72 | 151285 | 29708 | 0.1964 |
| office_0 | prior_full | 12.9771 | 34.4827 | 43.3848 | -0.3519 | 187.66 | 62.55 | 156821 | 39665 | 0.2529 |
| room_0 | prior_100k | 11.2187 | 43.3971 | 47.1838 | 0.5022 | 176.82 | 35.36 | 100000 | 22512 | 0.2251 |
| office_0 | prior_100k | 12.9814 | 38.0074 | 45.2079 | 1.4712 | 177.58 | 35.52 | 100000 | 35944 | 0.3594 |
| room_0 | prior_25k | 11.2252 | 41.3868 | 46.1027 | -0.5789 | 166.34 | 55.45 | 25000 | 10037 | 0.4015 |
| office_0 | prior_25k | 13.0151 | 37.5866 | 44.8669 | 1.1301 | 163.19 | 32.64 | 25000 | 12285 | 0.4914 |
| room_0 | prior_25k_full_none | 11.2252 | 43.5949 | 46.6438 | -0.0378 | 163.88 | 21.85 | 25000 | 9810 | 0.3924 |
| office_0 | prior_25k_full_none | 13.0141 | 35.0507 | 43.3975 | -0.3392 | 164.77 | 54.92 | 25000 | 10920 | 0.4368 |

## Object Survival

| scene | label | target_object_id | category | prior_object_id | original | inserted | insert_ratio | survived@3000 | ratio@3000 | survived@15000 | ratio@15000 |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| room_0 | prior_full | 6 | lamp | replica_room_0_obj_6 | 15786 | 15786 | 1.0000 | 8437 | 0.5345 | 2359 | 0.1494 |
| room_0 | prior_full | 9 | sofa | replica_room_0_obj_9 | 47762 | 47762 | 1.0000 | 45365 | 0.9498 | 10924 | 0.2287 |
| room_0 | prior_full | 77 | sofa | replica_room_0_obj_77 | 53683 | 53683 | 1.0000 | 51549 | 0.9602 | 11942 | 0.2225 |
| room_0 | prior_full | 74 | chair | replica_room_0_obj_74 | 34054 | 34054 | 1.0000 | 32952 | 0.9676 | 4483 | 0.1316 |
| office_0 | prior_full | 9 | sofa | replica_office_0_obj_9 | 45382 | 45382 | 1.0000 | 42356 | 0.9333 | 15030 | 0.3312 |
| office_0 | prior_full | 7 | sofa | replica_office_0_obj_7 | 35493 | 35493 | 1.0000 | 31809 | 0.8962 | 3402 | 0.0958 |
| office_0 | prior_full | 58 | table | replica_office_0_obj_58 | 32030 | 32030 | 1.0000 | 30673 | 0.9576 | 10066 | 0.3143 |
| office_0 | prior_full | 61 | chair | replica_office_0_obj_61 | 43916 | 43916 | 1.0000 | 42775 | 0.9740 | 11167 | 0.2543 |
| room_0 | prior_100k | 6 | lamp | replica_room_0_obj_6 | 15786 | 10434 | 0.6610 | 4488 | 0.4301 | 1568 | 0.1503 |
| room_0 | prior_100k | 9 | sofa | replica_room_0_obj_9 | 47762 | 31571 | 0.6610 | 29425 | 0.9320 | 8839 | 0.2800 |
| room_0 | prior_100k | 77 | sofa | replica_room_0_obj_77 | 53683 | 35485 | 0.6610 | 33917 | 0.9558 | 9067 | 0.2555 |
| room_0 | prior_100k | 74 | chair | replica_room_0_obj_74 | 34054 | 22510 | 0.6610 | 21556 | 0.9576 | 3038 | 0.1350 |
| office_0 | prior_100k | 9 | sofa | replica_office_0_obj_9 | 45382 | 28939 | 0.6377 | 26749 | 0.9243 | 12368 | 0.4274 |
| office_0 | prior_100k | 7 | sofa | replica_office_0_obj_7 | 35493 | 22633 | 0.6377 | 20009 | 0.8841 | 5642 | 0.2493 |
| office_0 | prior_100k | 58 | table | replica_office_0_obj_58 | 32030 | 20424 | 0.6377 | 19428 | 0.9512 | 8334 | 0.4080 |
| office_0 | prior_100k | 61 | chair | replica_office_0_obj_61 | 43916 | 28004 | 0.6377 | 26837 | 0.9583 | 9600 | 0.3428 |
| room_0 | prior_25k | 6 | lamp | replica_room_0_obj_6 | 15786 | 2609 | 0.1653 | 1709 | 0.6550 | 994 | 0.3810 |
| room_0 | prior_25k | 9 | sofa | replica_room_0_obj_9 | 47762 | 7893 | 0.1653 | 7306 | 0.9256 | 4036 | 0.5113 |
| room_0 | prior_25k | 77 | sofa | replica_room_0_obj_77 | 53683 | 8871 | 0.1652 | 8349 | 0.9412 | 3062 | 0.3452 |
| room_0 | prior_25k | 74 | chair | replica_room_0_obj_74 | 34054 | 5627 | 0.1652 | 5143 | 0.9140 | 1945 | 0.3457 |
| office_0 | prior_25k | 9 | sofa | replica_office_0_obj_9 | 45382 | 7235 | 0.1594 | 6631 | 0.9165 | 4413 | 0.6100 |
| office_0 | prior_25k | 7 | sofa | replica_office_0_obj_7 | 35493 | 5658 | 0.1594 | 4665 | 0.8245 | 1753 | 0.3098 |
| office_0 | prior_25k | 58 | table | replica_office_0_obj_58 | 32030 | 5106 | 0.1594 | 4826 | 0.9452 | 2487 | 0.4871 |
| office_0 | prior_25k | 61 | chair | replica_office_0_obj_61 | 43916 | 7001 | 0.1594 | 6412 | 0.9159 | 3632 | 0.5188 |
| room_0 | prior_25k_full_none | 6 | lamp | replica_room_0_obj_6 | 15786 | 2609 | 0.1653 | 1538 | 0.5895 | 859 | 0.3292 |
| room_0 | prior_25k_full_none | 9 | sofa | replica_room_0_obj_9 | 47762 | 7893 | 0.1653 | 7353 | 0.9316 | 3692 | 0.4678 |
| room_0 | prior_25k_full_none | 77 | sofa | replica_room_0_obj_77 | 53683 | 8871 | 0.1652 | 8383 | 0.9450 | 3503 | 0.3949 |
| room_0 | prior_25k_full_none | 74 | chair | replica_room_0_obj_74 | 34054 | 5627 | 0.1652 | 5102 | 0.9067 | 1756 | 0.3121 |
| office_0 | prior_25k_full_none | 9 | sofa | replica_office_0_obj_9 | 45382 | 7235 | 0.1594 | 6589 | 0.9107 | 4045 | 0.5591 |
| office_0 | prior_25k_full_none | 7 | sofa | replica_office_0_obj_7 | 35493 | 5658 | 0.1594 | 4698 | 0.8303 | 1173 | 0.2073 |
| office_0 | prior_25k_full_none | 58 | table | replica_office_0_obj_58 | 32030 | 5106 | 0.1594 | 4809 | 0.9418 | 2430 | 0.4759 |
| office_0 | prior_25k_full_none | 61 | chair | replica_office_0_obj_61 | 43916 | 7001 | 0.1594 | 6428 | 0.9182 | 3272 | 0.4674 |

## Notes

- `room_0` baseline absolute final PSNR: 46.6816; baseline 3000-iter target PSNR: 41.6301
- `office_0` baseline absolute final PSNR: 43.7367; baseline 3000-iter target PSNR: 36.5802
- 해석은 absolute 값과 함께 scene별 baseline 대비 delta를 우선 본다.

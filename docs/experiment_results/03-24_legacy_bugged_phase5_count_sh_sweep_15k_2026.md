# Replica Gaussian-Direct Phase 5.2 Count/SH Sweep (15K)

- Date: 2026-03-24
- Dataset family: `surface_rgb_roomwide_v2_384`
- Scenes: `room_0`, `office_0`
- Protection: `none`
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
| room_0 | prior_50k | 11.2217 | 42.9446 | 46.6097 | -0.0719 | 168.28 | 33.66 | 50000 | 15187 | 0.3037 |
| office_0 | prior_50k | 12.9963 | 35.3083 | 44.1429 | 0.4062 | 169.64 | 56.55 | 50000 | 17911 | 0.3582 |
| room_0 | prior_75k | 11.2201 | 42.8880 | 46.5026 | -0.1790 | 172.84 | 23.05 | 75000 | 15414 | 0.2055 |
| office_0 | prior_75k | 12.9865 | 37.3706 | 43.7640 | 0.0272 | 174.10 | 34.82 | 75000 | 29162 | 0.3888 |
| room_0 | prior_100k_geo | 11.2159 | 43.5107 | 47.0712 | 0.3896 | 170.26 | 22.70 | 100000 | 13027 | 0.1303 |
| office_0 | prior_100k_geo | 12.9367 | 33.7754 | 43.6963 | -0.0405 | 174.41 | 58.14 | 100000 | 26918 | 0.2692 |
| room_0 | prior_50k_geo | 11.2182 | 42.9553 | 46.3996 | -0.2821 | 167.66 | 22.35 | 50000 | 15032 | 0.3006 |
| office_0 | prior_50k_geo | 12.9541 | 37.7278 | 44.1596 | 0.4228 | 167.74 | 33.55 | 50000 | 19163 | 0.3833 |

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
| room_0 | prior_50k | 6 | lamp | replica_room_0_obj_6 | 15786 | 5217 | 0.3305 | 2574 | 0.4934 | 1432 | 0.2745 |
| room_0 | prior_50k | 9 | sofa | replica_room_0_obj_9 | 47762 | 15786 | 0.3305 | 14571 | 0.9230 | 6436 | 0.4077 |
| room_0 | prior_50k | 77 | sofa | replica_room_0_obj_77 | 53683 | 17742 | 0.3305 | 16540 | 0.9323 | 4537 | 0.2557 |
| room_0 | prior_50k | 74 | chair | replica_room_0_obj_74 | 34054 | 11255 | 0.3305 | 10379 | 0.9222 | 2782 | 0.2472 |
| office_0 | prior_50k | 9 | sofa | replica_office_0_obj_9 | 45382 | 14469 | 0.3188 | 13057 | 0.9024 | 6302 | 0.4356 |
| office_0 | prior_50k | 7 | sofa | replica_office_0_obj_7 | 35493 | 11317 | 0.3189 | 9825 | 0.8682 | 2344 | 0.2071 |
| office_0 | prior_50k | 58 | table | replica_office_0_obj_58 | 32030 | 10212 | 0.3188 | 9573 | 0.9374 | 4421 | 0.4329 |
| office_0 | prior_50k | 61 | chair | replica_office_0_obj_61 | 43916 | 14002 | 0.3188 | 12473 | 0.8908 | 4844 | 0.3460 |
| room_0 | prior_75k | 6 | lamp | replica_room_0_obj_6 | 15786 | 7826 | 0.4958 | 3756 | 0.4799 | 1580 | 0.2019 |
| room_0 | prior_75k | 9 | sofa | replica_room_0_obj_9 | 47762 | 23678 | 0.4957 | 22028 | 0.9303 | 5479 | 0.2314 |
| room_0 | prior_75k | 77 | sofa | replica_room_0_obj_77 | 53683 | 26614 | 0.4958 | 25133 | 0.9444 | 5854 | 0.2200 |
| room_0 | prior_75k | 74 | chair | replica_room_0_obj_74 | 34054 | 16882 | 0.4957 | 15679 | 0.9287 | 2501 | 0.1481 |
| office_0 | prior_75k | 9 | sofa | replica_office_0_obj_9 | 45382 | 21704 | 0.4783 | 19894 | 0.9166 | 9099 | 0.4192 |
| office_0 | prior_75k | 7 | sofa | replica_office_0_obj_7 | 35493 | 16975 | 0.4783 | 14656 | 0.8634 | 4753 | 0.2800 |
| office_0 | prior_75k | 58 | table | replica_office_0_obj_58 | 32030 | 15318 | 0.4782 | 14569 | 0.9511 | 5974 | 0.3900 |
| office_0 | prior_75k | 61 | chair | replica_office_0_obj_61 | 43916 | 21003 | 0.4783 | 19552 | 0.9309 | 9336 | 0.4445 |
| room_0 | prior_100k_geo | 6 | lamp | replica_room_0_obj_6 | 15786 | 10434 | 0.6610 | 3375 | 0.3235 | 1389 | 0.1331 |
| room_0 | prior_100k_geo | 9 | sofa | replica_room_0_obj_9 | 47762 | 31571 | 0.6610 | 22249 | 0.7047 | 3856 | 0.1221 |
| room_0 | prior_100k_geo | 77 | sofa | replica_room_0_obj_77 | 53683 | 35485 | 0.6610 | 30410 | 0.8570 | 6420 | 0.1809 |
| room_0 | prior_100k_geo | 74 | chair | replica_room_0_obj_74 | 34054 | 22510 | 0.6610 | 19614 | 0.8713 | 1362 | 0.0605 |
| office_0 | prior_100k_geo | 9 | sofa | replica_office_0_obj_9 | 45382 | 28939 | 0.6377 | 18517 | 0.6399 | 9045 | 0.3126 |
| office_0 | prior_100k_geo | 7 | sofa | replica_office_0_obj_7 | 35493 | 22633 | 0.6377 | 12819 | 0.5664 | 3918 | 0.1731 |
| office_0 | prior_100k_geo | 58 | table | replica_office_0_obj_58 | 32030 | 20424 | 0.6377 | 15912 | 0.7791 | 7859 | 0.3848 |
| office_0 | prior_100k_geo | 61 | chair | replica_office_0_obj_61 | 43916 | 28004 | 0.6377 | 16697 | 0.5962 | 6096 | 0.2177 |
| room_0 | prior_50k_geo | 6 | lamp | replica_room_0_obj_6 | 15786 | 5217 | 0.3305 | 2470 | 0.4735 | 1479 | 0.2835 |
| room_0 | prior_50k_geo | 9 | sofa | replica_room_0_obj_9 | 47762 | 15786 | 0.3305 | 11740 | 0.7437 | 5805 | 0.3677 |
| room_0 | prior_50k_geo | 77 | sofa | replica_room_0_obj_77 | 53683 | 17742 | 0.3305 | 14989 | 0.8448 | 5853 | 0.3299 |
| room_0 | prior_50k_geo | 74 | chair | replica_room_0_obj_74 | 34054 | 11255 | 0.3305 | 9509 | 0.8449 | 1895 | 0.1684 |
| office_0 | prior_50k_geo | 9 | sofa | replica_office_0_obj_9 | 45382 | 14469 | 0.3188 | 10166 | 0.7026 | 7281 | 0.5032 |
| office_0 | prior_50k_geo | 7 | sofa | replica_office_0_obj_7 | 35493 | 11317 | 0.3189 | 5840 | 0.5160 | 2894 | 0.2557 |
| office_0 | prior_50k_geo | 58 | table | replica_office_0_obj_58 | 32030 | 10212 | 0.3188 | 8344 | 0.8171 | 4667 | 0.4570 |
| office_0 | prior_50k_geo | 61 | chair | replica_office_0_obj_61 | 43916 | 14002 | 0.3188 | 8447 | 0.6033 | 4321 | 0.3086 |


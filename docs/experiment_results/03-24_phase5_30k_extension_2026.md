# Replica Gaussian-Direct Phase 5.3 30K Extension

- Date: 2026-03-24
- Dataset family: `surface_rgb_roomwide_v2_384`
- Scenes: `room_0`, `office_0`
- Protection: `none`
- 비교 기준: absolute PSNR/SSIM/LPIPS와 scene별 baseline_30000 대비 delta

## Summary

| scene | label | iter_0_psnr | iter_3000_psnr | iter_15000_psnr | final_psnr | final_delta_vs_baseline | total_time_sec | ttt_sec | prior_inserted_total | survived@30000 | survival@30000 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| room_0 | baseline_30000 | 11.2341 | 40.3181 | 46.7225 | 47.6996 | n/a | 282.46 | 18.83 | 0 | n/a | n/a |
| office_0 | baseline_30000 | 13.0536 | 34.6466 | 44.3083 | 46.1383 | n/a | 282.50 | 28.25 | 0 | n/a | n/a |
| room_0 | prior_100k_30000 | 11.4910 | 43.4635 | 47.3797 | 48.3649 | 0.6653 | 326.57 | 21.77 | 100000 | 44550 | 0.4455 |
| office_0 | prior_100k_30000 | 13.2190 | 34.3185 | 43.6455 | 46.0347 | -0.1036 | 312.60 | 52.10 | 100000 | 33834 | 0.3383 |
| room_0 | prior_25k_30000 | 11.4159 | 43.5760 | 47.2217 | 48.1756 | 0.4759 | 294.90 | 19.66 | 25000 | 14323 | 0.5729 |
| office_0 | prior_25k_30000 | 13.2005 | 34.8535 | 44.3270 | 45.6590 | -0.4793 | 289.84 | 28.98 | 25000 | 11789 | 0.4716 |
| room_0 | prior_25k_full_none_30000 | 11.4255 | 43.6166 | 46.9980 | 48.3015 | 0.6018 | 296.27 | 19.75 | 25000 | 14047 | 0.5619 |
| office_0 | prior_25k_full_none_30000 | 13.1960 | 37.0524 | 44.6511 | 46.4116 | 0.2733 | 286.11 | 28.61 | 25000 | 11870 | 0.4748 |
| room_0 | prior_50k_30000 | 11.4716 | 43.7568 | 47.2084 | 47.5187 | -0.1810 | 304.67 | 20.31 | 50000 | 25481 | 0.5096 |
| office_0 | prior_50k_30000 | 13.2175 | 32.4897 | 42.9248 | 44.9883 | -1.1500 | 303.61 | 50.60 | 50000 | 20388 | 0.4078 |
| room_0 | prior_75k_30000 | 11.4828 | 43.3035 | 46.9920 | 47.8532 | 0.1536 | 311.28 | 20.75 | 75000 | 34490 | 0.4599 |
| office_0 | prior_75k_30000 | 13.2202 | 37.5268 | 44.2112 | 46.1032 | -0.0351 | 305.34 | 30.53 | 75000 | 27128 | 0.3617 |
| room_0 | prior_100k_geo_30000 | 11.3438 | 41.9670 | 45.5535 | 47.9267 | 0.2270 | 329.23 | 21.95 | 100000 | 53620 | 0.5362 |
| office_0 | prior_100k_geo_30000 | 12.9248 | 34.9100 | 45.1086 | 46.3349 | 0.1966 | 311.53 | 31.15 | 100000 | 34000 | 0.3400 |

## Object Survival

| scene | label | target_object_id | category | prior_object_id | original | inserted | insert_ratio | survived@3000 | ratio@3000 | survived@30000 | ratio@30000 |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| room_0 | prior_100k_30000 | 6 | lamp | replica_room_0_obj_6 | 15786 | 10434 | 0.6610 | 1889 | 0.1810 | 384 | 0.0368 |
| room_0 | prior_100k_30000 | 9 | sofa | replica_room_0_obj_9 | 47762 | 31571 | 0.6610 | 28610 | 0.9062 | 15066 | 0.4772 |
| room_0 | prior_100k_30000 | 77 | sofa | replica_room_0_obj_77 | 53683 | 35485 | 0.6610 | 31873 | 0.8982 | 16430 | 0.4630 |
| room_0 | prior_100k_30000 | 74 | chair | replica_room_0_obj_74 | 34054 | 22510 | 0.6610 | 20491 | 0.9103 | 12670 | 0.5629 |
| office_0 | prior_100k_30000 | 9 | sofa | replica_office_0_obj_9 | 45382 | 28939 | 0.6377 | 23716 | 0.8195 | 8861 | 0.3062 |
| office_0 | prior_100k_30000 | 7 | sofa | replica_office_0_obj_7 | 35493 | 22633 | 0.6377 | 12019 | 0.5310 | 4055 | 0.1792 |
| office_0 | prior_100k_30000 | 58 | table | replica_office_0_obj_58 | 32030 | 20424 | 0.6377 | 16618 | 0.8137 | 6890 | 0.3373 |
| office_0 | prior_100k_30000 | 61 | chair | replica_office_0_obj_61 | 43916 | 28004 | 0.6377 | 23851 | 0.8517 | 14028 | 0.5009 |
| room_0 | prior_25k_30000 | 6 | lamp | replica_room_0_obj_6 | 15786 | 2609 | 0.1653 | 720 | 0.2760 | 347 | 0.1330 |
| room_0 | prior_25k_30000 | 9 | sofa | replica_room_0_obj_9 | 47762 | 7893 | 0.1653 | 7112 | 0.9011 | 4835 | 0.6126 |
| room_0 | prior_25k_30000 | 77 | sofa | replica_room_0_obj_77 | 53683 | 8871 | 0.1652 | 7867 | 0.8868 | 5017 | 0.5656 |
| room_0 | prior_25k_30000 | 74 | chair | replica_room_0_obj_74 | 34054 | 5627 | 0.1652 | 5314 | 0.9444 | 4124 | 0.7329 |
| office_0 | prior_25k_30000 | 9 | sofa | replica_office_0_obj_9 | 45382 | 7235 | 0.1594 | 6218 | 0.8594 | 3071 | 0.4245 |
| office_0 | prior_25k_30000 | 7 | sofa | replica_office_0_obj_7 | 35493 | 5658 | 0.1594 | 3622 | 0.6402 | 1490 | 0.2633 |
| office_0 | prior_25k_30000 | 58 | table | replica_office_0_obj_58 | 32030 | 5106 | 0.1594 | 4277 | 0.8376 | 2359 | 0.4620 |
| office_0 | prior_25k_30000 | 61 | chair | replica_office_0_obj_61 | 43916 | 7001 | 0.1594 | 6371 | 0.9100 | 4869 | 0.6955 |
| room_0 | prior_25k_full_none_30000 | 6 | lamp | replica_room_0_obj_6 | 15786 | 2609 | 0.1653 | 817 | 0.3131 | 352 | 0.1349 |
| room_0 | prior_25k_full_none_30000 | 9 | sofa | replica_room_0_obj_9 | 47762 | 7893 | 0.1653 | 7184 | 0.9102 | 4798 | 0.6079 |
| room_0 | prior_25k_full_none_30000 | 77 | sofa | replica_room_0_obj_77 | 53683 | 8871 | 0.1652 | 7934 | 0.8944 | 4831 | 0.5446 |
| room_0 | prior_25k_full_none_30000 | 74 | chair | replica_room_0_obj_74 | 34054 | 5627 | 0.1652 | 5306 | 0.9430 | 4066 | 0.7226 |
| office_0 | prior_25k_full_none_30000 | 9 | sofa | replica_office_0_obj_9 | 45382 | 7235 | 0.1594 | 6274 | 0.8672 | 3193 | 0.4413 |
| office_0 | prior_25k_full_none_30000 | 7 | sofa | replica_office_0_obj_7 | 35493 | 5658 | 0.1594 | 3779 | 0.6679 | 1430 | 0.2527 |
| office_0 | prior_25k_full_none_30000 | 58 | table | replica_office_0_obj_58 | 32030 | 5106 | 0.1594 | 4296 | 0.8414 | 2342 | 0.4587 |
| office_0 | prior_25k_full_none_30000 | 61 | chair | replica_office_0_obj_61 | 43916 | 7001 | 0.1594 | 6379 | 0.9112 | 4905 | 0.7006 |
| room_0 | prior_50k_30000 | 6 | lamp | replica_room_0_obj_6 | 15786 | 5217 | 0.3305 | 1063 | 0.2038 | 460 | 0.0882 |
| room_0 | prior_50k_30000 | 9 | sofa | replica_room_0_obj_9 | 47762 | 15786 | 0.3305 | 14367 | 0.9101 | 8880 | 0.5625 |
| room_0 | prior_50k_30000 | 77 | sofa | replica_room_0_obj_77 | 53683 | 17742 | 0.3305 | 15963 | 0.8997 | 8937 | 0.5037 |
| room_0 | prior_50k_30000 | 74 | chair | replica_room_0_obj_74 | 34054 | 11255 | 0.3305 | 10415 | 0.9254 | 7204 | 0.6401 |
| office_0 | prior_50k_30000 | 9 | sofa | replica_office_0_obj_9 | 45382 | 14469 | 0.3188 | 12256 | 0.8471 | 5310 | 0.3670 |
| office_0 | prior_50k_30000 | 7 | sofa | replica_office_0_obj_7 | 35493 | 11317 | 0.3189 | 6751 | 0.5965 | 2679 | 0.2367 |
| office_0 | prior_50k_30000 | 58 | table | replica_office_0_obj_58 | 32030 | 10212 | 0.3188 | 8405 | 0.8231 | 4156 | 0.4070 |
| office_0 | prior_50k_30000 | 61 | chair | replica_office_0_obj_61 | 43916 | 14002 | 0.3188 | 12193 | 0.8708 | 8243 | 0.5887 |
| room_0 | prior_75k_30000 | 6 | lamp | replica_room_0_obj_6 | 15786 | 7826 | 0.4958 | 1501 | 0.1918 | 350 | 0.0447 |
| room_0 | prior_75k_30000 | 9 | sofa | replica_room_0_obj_9 | 47762 | 23678 | 0.4957 | 21365 | 0.9023 | 12194 | 0.5150 |
| room_0 | prior_75k_30000 | 77 | sofa | replica_room_0_obj_77 | 53683 | 26614 | 0.4958 | 23977 | 0.9009 | 12205 | 0.4586 |
| room_0 | prior_75k_30000 | 74 | chair | replica_room_0_obj_74 | 34054 | 16882 | 0.4957 | 15375 | 0.9107 | 9741 | 0.5770 |
| office_0 | prior_75k_30000 | 9 | sofa | replica_office_0_obj_9 | 45382 | 21704 | 0.4783 | 17892 | 0.8244 | 7214 | 0.3324 |
| office_0 | prior_75k_30000 | 7 | sofa | replica_office_0_obj_7 | 35493 | 16975 | 0.4783 | 9435 | 0.5558 | 3265 | 0.1923 |
| office_0 | prior_75k_30000 | 58 | table | replica_office_0_obj_58 | 32030 | 15318 | 0.4782 | 12643 | 0.8254 | 5848 | 0.3818 |
| office_0 | prior_75k_30000 | 61 | chair | replica_office_0_obj_61 | 43916 | 21003 | 0.4783 | 17876 | 0.8511 | 10801 | 0.5143 |
| room_0 | prior_100k_geo_30000 | 6 | lamp | replica_room_0_obj_6 | 15786 | 10434 | 0.6610 | 852 | 0.0817 | 610 | 0.0585 |
| room_0 | prior_100k_geo_30000 | 9 | sofa | replica_room_0_obj_9 | 47762 | 31571 | 0.6610 | 27716 | 0.8779 | 18583 | 0.5886 |
| room_0 | prior_100k_geo_30000 | 77 | sofa | replica_room_0_obj_77 | 53683 | 35485 | 0.6610 | 31906 | 0.8991 | 21849 | 0.6157 |
| room_0 | prior_100k_geo_30000 | 74 | chair | replica_room_0_obj_74 | 34054 | 22510 | 0.6610 | 18710 | 0.8312 | 12578 | 0.5588 |
| office_0 | prior_100k_geo_30000 | 9 | sofa | replica_office_0_obj_9 | 45382 | 28939 | 0.6377 | 17631 | 0.6092 | 10218 | 0.3531 |
| office_0 | prior_100k_geo_30000 | 7 | sofa | replica_office_0_obj_7 | 35493 | 22633 | 0.6377 | 7369 | 0.3256 | 4283 | 0.1892 |
| office_0 | prior_100k_geo_30000 | 58 | table | replica_office_0_obj_58 | 32030 | 20424 | 0.6377 | 13740 | 0.6727 | 9990 | 0.4891 |
| office_0 | prior_100k_geo_30000 | 61 | chair | replica_office_0_obj_61 | 43916 | 28004 | 0.6377 | 17459 | 0.6234 | 9509 | 0.3396 |


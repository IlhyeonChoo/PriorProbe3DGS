# Replica Gaussian-Direct Phase 5.3 30K Extension

- Date: 2026-03-24
- Dataset family: `surface_rgb_roomwide_v2_384`
- Scenes: `room_0`, `office_0`
- Protection: `none`
- 비교 기준: absolute PSNR/SSIM/LPIPS와 scene별 baseline_30000 대비 delta

## Summary

| scene | label | iter_0_psnr | iter_3000_psnr | iter_15000_psnr | final_psnr | final_delta_vs_baseline | total_time_sec | ttt_sec | prior_inserted_total | survived@30000 | survival@30000 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| room_0 | baseline_30000 | 11.2341 | 42.7009 | 46.8233 | 48.1335 | n/a | 283.54 | 28.35 | 0 | n/a | n/a |
| office_0 | baseline_30000 | 13.0536 | 36.1188 | 45.0428 | 46.2664 | n/a | 274.47 | 27.45 | 0 | n/a | n/a |
| room_0 | prior_100k_30000 | 11.2188 | 43.1965 | 46.8056 | 48.1127 | -0.0208 | 303.88 | 30.39 | 100000 | 21205 | 0.2120 |
| office_0 | prior_100k_30000 | 12.9818 | 35.0194 | 42.9184 | 45.7691 | -0.4972 | 302.37 | 50.39 | 100000 | 30712 | 0.3071 |
| room_0 | prior_full_30000 | 11.2175 | 42.8262 | 46.9851 | 47.8150 | -0.3185 | 314.97 | 31.50 | 151285 | 31070 | 0.2054 |
| office_0 | prior_full_30000 | 12.9771 | 35.3702 | 44.7785 | 45.9420 | -0.3244 | 321.36 | 53.56 | 156821 | 45292 | 0.2888 |
| room_0 | prior_25k_30000 | 11.2253 | 43.6152 | 46.6643 | 47.5916 | -0.5419 | 289.87 | 28.99 | 25000 | 9745 | 0.3898 |
| office_0 | prior_25k_30000 | 13.0151 | 37.0439 | 43.4740 | 45.6456 | -0.6207 | 283.72 | 28.37 | 25000 | 10720 | 0.4288 |
| room_0 | prior_50k_30000 | 11.2217 | 43.5415 | 46.3283 | 48.0214 | -0.1122 | 291.55 | 29.15 | 50000 | 15798 | 0.3160 |
| office_0 | prior_50k_30000 | 12.9972 | 36.8885 | 44.8291 | 46.5339 | 0.2675 | 287.90 | 28.79 | 50000 | 19390 | 0.3878 |
| room_0 | prior_75k_30000 | 11.2199 | 42.7014 | 46.6114 | 48.2926 | 0.1590 | 307.35 | 30.73 | 75000 | 22023 | 0.2936 |
| office_0 | prior_75k_30000 | 12.9877 | 36.9619 | 44.6466 | 46.3187 | 0.0523 | 297.37 | 29.74 | 75000 | 26605 | 0.3547 |
| room_0 | prior_100k_geo_30000 | 11.2163 | 42.8829 | 46.3159 | 48.1126 | -0.0210 | 306.68 | 30.67 | 100000 | 21788 | 0.2179 |
| office_0 | prior_100k_geo_30000 | 12.9371 | 34.5055 | 41.9527 | 45.4472 | -0.8192 | 299.26 | 49.88 | 100000 | 28055 | 0.2806 |
| room_0 | prior_50k_geo_30000 | 11.2179 | 42.1423 | 45.7288 | 47.7560 | -0.3776 | 294.34 | 49.06 | 50000 | 12718 | 0.2544 |
| office_0 | prior_50k_geo_30000 | 12.9549 | 36.7529 | 42.4646 | 45.2767 | -0.9896 | 288.17 | 28.82 | 50000 | 17874 | 0.3575 |

## Object Survival

| scene | label | target_object_id | category | prior_object_id | original | inserted | insert_ratio | survived@3000 | ratio@3000 | survived@30000 | ratio@30000 |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| room_0 | prior_100k_30000 | 6 | lamp | replica_room_0_obj_6 | 15786 | 10434 | 0.6610 | 4874 | 0.4671 | 1364 | 0.1307 |
| room_0 | prior_100k_30000 | 9 | sofa | replica_room_0_obj_9 | 47762 | 31571 | 0.6610 | 29483 | 0.9339 | 8508 | 0.2695 |
| room_0 | prior_100k_30000 | 77 | sofa | replica_room_0_obj_77 | 53683 | 35485 | 0.6610 | 33494 | 0.9439 | 8237 | 0.2321 |
| room_0 | prior_100k_30000 | 74 | chair | replica_room_0_obj_74 | 34054 | 22510 | 0.6610 | 21453 | 0.9530 | 3096 | 0.1375 |
| office_0 | prior_100k_30000 | 9 | sofa | replica_office_0_obj_9 | 45382 | 28939 | 0.6377 | 26420 | 0.9130 | 11623 | 0.4016 |
| office_0 | prior_100k_30000 | 7 | sofa | replica_office_0_obj_7 | 35493 | 22633 | 0.6377 | 19633 | 0.8675 | 3548 | 0.1568 |
| office_0 | prior_100k_30000 | 58 | table | replica_office_0_obj_58 | 32030 | 20424 | 0.6377 | 19525 | 0.9560 | 8492 | 0.4158 |
| office_0 | prior_100k_30000 | 61 | chair | replica_office_0_obj_61 | 43916 | 28004 | 0.6377 | 26720 | 0.9541 | 7049 | 0.2517 |
| room_0 | prior_full_30000 | 6 | lamp | replica_room_0_obj_6 | 15786 | 15786 | 1.0000 | 8449 | 0.5352 | 1872 | 0.1186 |
| room_0 | prior_full_30000 | 9 | sofa | replica_room_0_obj_9 | 47762 | 47762 | 1.0000 | 45777 | 0.9584 | 12062 | 0.2525 |
| room_0 | prior_full_30000 | 77 | sofa | replica_room_0_obj_77 | 53683 | 53683 | 1.0000 | 51453 | 0.9585 | 11476 | 0.2138 |
| room_0 | prior_full_30000 | 74 | chair | replica_room_0_obj_74 | 34054 | 34054 | 1.0000 | 32889 | 0.9658 | 5660 | 0.1662 |
| office_0 | prior_full_30000 | 9 | sofa | replica_office_0_obj_9 | 45382 | 45382 | 1.0000 | 42060 | 0.9268 | 13519 | 0.2979 |
| office_0 | prior_full_30000 | 7 | sofa | replica_office_0_obj_7 | 35493 | 35493 | 1.0000 | 31836 | 0.8970 | 7353 | 0.2072 |
| office_0 | prior_full_30000 | 58 | table | replica_office_0_obj_58 | 32030 | 32030 | 1.0000 | 30826 | 0.9624 | 11571 | 0.3613 |
| office_0 | prior_full_30000 | 61 | chair | replica_office_0_obj_61 | 43916 | 43916 | 1.0000 | 42479 | 0.9673 | 12849 | 0.2926 |
| room_0 | prior_25k_30000 | 6 | lamp | replica_room_0_obj_6 | 15786 | 2609 | 0.1653 | 1551 | 0.5945 | 850 | 0.3258 |
| room_0 | prior_25k_30000 | 9 | sofa | replica_room_0_obj_9 | 47762 | 7893 | 0.1653 | 7354 | 0.9317 | 4200 | 0.5321 |
| room_0 | prior_25k_30000 | 77 | sofa | replica_room_0_obj_77 | 53683 | 8871 | 0.1652 | 8304 | 0.9361 | 3214 | 0.3623 |
| room_0 | prior_25k_30000 | 74 | chair | replica_room_0_obj_74 | 34054 | 5627 | 0.1652 | 5166 | 0.9181 | 1481 | 0.2632 |
| office_0 | prior_25k_30000 | 9 | sofa | replica_office_0_obj_9 | 45382 | 7235 | 0.1594 | 6642 | 0.9180 | 3477 | 0.4806 |
| office_0 | prior_25k_30000 | 7 | sofa | replica_office_0_obj_7 | 35493 | 5658 | 0.1594 | 4650 | 0.8218 | 1548 | 0.2736 |
| office_0 | prior_25k_30000 | 58 | table | replica_office_0_obj_58 | 32030 | 5106 | 0.1594 | 4803 | 0.9407 | 2074 | 0.4062 |
| office_0 | prior_25k_30000 | 61 | chair | replica_office_0_obj_61 | 43916 | 7001 | 0.1594 | 6392 | 0.9130 | 3621 | 0.5172 |
| room_0 | prior_50k_30000 | 6 | lamp | replica_room_0_obj_6 | 15786 | 5217 | 0.3305 | 2289 | 0.4388 | 977 | 0.1873 |
| room_0 | prior_50k_30000 | 9 | sofa | replica_room_0_obj_9 | 47762 | 15786 | 0.3305 | 14559 | 0.9223 | 6091 | 0.3858 |
| room_0 | prior_50k_30000 | 77 | sofa | replica_room_0_obj_77 | 53683 | 17742 | 0.3305 | 16542 | 0.9324 | 5997 | 0.3380 |
| room_0 | prior_50k_30000 | 74 | chair | replica_room_0_obj_74 | 34054 | 11255 | 0.3305 | 10337 | 0.9184 | 2733 | 0.2428 |
| office_0 | prior_50k_30000 | 9 | sofa | replica_office_0_obj_9 | 45382 | 14469 | 0.3188 | 13135 | 0.9078 | 6044 | 0.4177 |
| office_0 | prior_50k_30000 | 7 | sofa | replica_office_0_obj_7 | 35493 | 11317 | 0.3189 | 9598 | 0.8481 | 3252 | 0.2874 |
| office_0 | prior_50k_30000 | 58 | table | replica_office_0_obj_58 | 32030 | 10212 | 0.3188 | 9668 | 0.9467 | 4278 | 0.4189 |
| office_0 | prior_50k_30000 | 61 | chair | replica_office_0_obj_61 | 43916 | 14002 | 0.3188 | 12702 | 0.9072 | 5816 | 0.4154 |
| room_0 | prior_75k_30000 | 6 | lamp | replica_room_0_obj_6 | 15786 | 7826 | 0.4958 | 3257 | 0.4162 | 1638 | 0.2093 |
| room_0 | prior_75k_30000 | 9 | sofa | replica_room_0_obj_9 | 47762 | 23678 | 0.4957 | 22058 | 0.9316 | 8750 | 0.3695 |
| room_0 | prior_75k_30000 | 77 | sofa | replica_room_0_obj_77 | 53683 | 26614 | 0.4958 | 25009 | 0.9397 | 7492 | 0.2815 |
| room_0 | prior_75k_30000 | 74 | chair | replica_room_0_obj_74 | 34054 | 16882 | 0.4957 | 15775 | 0.9344 | 4143 | 0.2454 |
| office_0 | prior_75k_30000 | 9 | sofa | replica_office_0_obj_9 | 45382 | 21704 | 0.4783 | 19784 | 0.9115 | 9308 | 0.4289 |
| office_0 | prior_75k_30000 | 7 | sofa | replica_office_0_obj_7 | 35493 | 16975 | 0.4783 | 14824 | 0.8733 | 3775 | 0.2224 |
| office_0 | prior_75k_30000 | 58 | table | replica_office_0_obj_58 | 32030 | 15318 | 0.4782 | 14508 | 0.9471 | 6321 | 0.4127 |
| office_0 | prior_75k_30000 | 61 | chair | replica_office_0_obj_61 | 43916 | 21003 | 0.4783 | 19712 | 0.9385 | 7201 | 0.3429 |
| room_0 | prior_100k_geo_30000 | 6 | lamp | replica_room_0_obj_6 | 15786 | 10434 | 0.6610 | 3320 | 0.3182 | 1847 | 0.1770 |
| room_0 | prior_100k_geo_30000 | 9 | sofa | replica_room_0_obj_9 | 47762 | 31571 | 0.6610 | 21948 | 0.6952 | 8333 | 0.2639 |
| room_0 | prior_100k_geo_30000 | 77 | sofa | replica_room_0_obj_77 | 53683 | 35485 | 0.6610 | 29409 | 0.8288 | 8349 | 0.2353 |
| room_0 | prior_100k_geo_30000 | 74 | chair | replica_room_0_obj_74 | 34054 | 22510 | 0.6610 | 19701 | 0.8752 | 3259 | 0.1448 |
| office_0 | prior_100k_geo_30000 | 9 | sofa | replica_office_0_obj_9 | 45382 | 28939 | 0.6377 | 18861 | 0.6518 | 10683 | 0.3692 |
| office_0 | prior_100k_geo_30000 | 7 | sofa | replica_office_0_obj_7 | 35493 | 22633 | 0.6377 | 11808 | 0.5217 | 3749 | 0.1656 |
| office_0 | prior_100k_geo_30000 | 58 | table | replica_office_0_obj_58 | 32030 | 20424 | 0.6377 | 15613 | 0.7644 | 8067 | 0.3950 |
| office_0 | prior_100k_geo_30000 | 61 | chair | replica_office_0_obj_61 | 43916 | 28004 | 0.6377 | 18545 | 0.6622 | 5556 | 0.1984 |
| room_0 | prior_50k_geo_30000 | 6 | lamp | replica_room_0_obj_6 | 15786 | 5217 | 0.3305 | 2122 | 0.4067 | 1201 | 0.2302 |
| room_0 | prior_50k_geo_30000 | 9 | sofa | replica_room_0_obj_9 | 47762 | 15786 | 0.3305 | 12270 | 0.7773 | 5277 | 0.3343 |
| room_0 | prior_50k_geo_30000 | 77 | sofa | replica_room_0_obj_77 | 53683 | 17742 | 0.3305 | 15171 | 0.8551 | 4173 | 0.2352 |
| room_0 | prior_50k_geo_30000 | 74 | chair | replica_room_0_obj_74 | 34054 | 11255 | 0.3305 | 9214 | 0.8187 | 2067 | 0.1837 |
| office_0 | prior_50k_geo_30000 | 9 | sofa | replica_office_0_obj_9 | 45382 | 14469 | 0.3188 | 9848 | 0.6806 | 6237 | 0.4311 |
| office_0 | prior_50k_geo_30000 | 7 | sofa | replica_office_0_obj_7 | 35493 | 11317 | 0.3189 | 6600 | 0.5832 | 2644 | 0.2336 |
| office_0 | prior_50k_geo_30000 | 58 | table | replica_office_0_obj_58 | 32030 | 10212 | 0.3188 | 8414 | 0.8239 | 4512 | 0.4418 |
| office_0 | prior_50k_geo_30000 | 61 | chair | replica_office_0_obj_61 | 43916 | 14002 | 0.3188 | 9434 | 0.6738 | 4481 | 0.3200 |


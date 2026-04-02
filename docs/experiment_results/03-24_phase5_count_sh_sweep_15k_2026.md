# Replica Gaussian-Direct Phase 5.2 Count/SH Sweep (15K)

- Date: 2026-03-24
- Dataset family: `surface_rgb_roomwide_v2_384`
- Scenes: `room_0`, `office_0`
- Protection: `none`
- 비교 기준: absolute PSNR/SSIM/LPIPS와 scene별 baseline 대비 delta

## Summary

| scene | label | iter_0_psnr | iter_3000_psnr | final_psnr | final_delta_vs_baseline | total_time_sec | ttt_sec | prior_inserted_total | survived@15000 | survival@15000 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| room_0 | baseline | 11.2341 | 42.2405 | 46.6062 | n/a | 162.57 | 32.51 | 0 | n/a | n/a |
| office_0 | baseline | 13.0536 | 34.1250 | 44.2005 | n/a | 162.72 | 32.54 | 0 | n/a | n/a |
| room_0 | prior_full | 11.5075 | 43.8670 | 46.3769 | -0.2293 | 196.08 | 39.22 | 151285 | 57473 | 0.3799 |
| office_0 | prior_full | 13.2171 | 34.8579 | 42.5710 | -1.6295 | 194.00 | 38.80 | 156821 | 45366 | 0.2893 |
| room_0 | prior_100k | 11.4880 | 42.4605 | 46.2671 | -0.3391 | 183.53 | 36.71 | 100000 | 44274 | 0.4427 |
| office_0 | prior_100k | 13.2181 | 34.9994 | 43.4852 | -0.7153 | 182.63 | 36.53 | 100000 | 34608 | 0.3461 |
| room_0 | prior_25k | 11.4240 | 43.3849 | 46.7003 | 0.0940 | 167.71 | 33.54 | 25000 | 13818 | 0.5527 |
| office_0 | prior_25k | 13.1983 | 36.5218 | 44.0838 | -0.1167 | 165.78 | 33.16 | 25000 | 11444 | 0.4578 |
| room_0 | prior_25k_full_none | 11.4252 | 43.5712 | 46.4243 | -0.1820 | 168.03 | 33.61 | 25000 | 14618 | 0.5847 |
| office_0 | prior_25k_full_none | 13.1945 | 37.7718 | 44.9459 | 0.7454 | 164.33 | 21.91 | 25000 | 12192 | 0.4877 |
| room_0 | prior_50k | 11.4659 | 43.3065 | 46.7460 | 0.1398 | 171.92 | 34.38 | 50000 | 24328 | 0.4866 |
| office_0 | prior_50k | 13.2163 | 34.0137 | 43.9683 | -0.2323 | 172.65 | 57.55 | 50000 | 20883 | 0.4177 |
| room_0 | prior_75k | 11.4786 | 43.3705 | 46.5383 | -0.0679 | 177.33 | 35.47 | 75000 | 35235 | 0.4698 |
| office_0 | prior_75k | 13.2248 | 35.9367 | 44.4419 | 0.2414 | 177.78 | 35.56 | 75000 | 28438 | 0.3792 |
| room_0 | prior_100k_geo | 11.3457 | 42.9687 | 46.6127 | 0.0065 | 188.77 | 37.75 | 100000 | 54553 | 0.5455 |
| office_0 | prior_100k_geo | 12.9274 | 34.2894 | 42.9495 | -1.2511 | 179.28 | 35.86 | 100000 | 33612 | 0.3361 |
| room_0 | prior_50k_geo | 11.2910 | 43.6846 | 46.0655 | -0.5408 | 176.66 | 35.33 | 50000 | 30873 | 0.6175 |
| office_0 | prior_50k_geo | 12.9535 | 35.7977 | 43.7817 | -0.4188 | 172.44 | 34.49 | 50000 | 24366 | 0.4873 |

## Object Survival

| scene | label | target_object_id | category | prior_object_id | original | inserted | insert_ratio | survived@3000 | ratio@3000 | survived@15000 | ratio@15000 |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| room_0 | prior_full | 6 | lamp | replica_room_0_obj_6 | 15786 | 15786 | 1.0000 | 3646 | 0.2310 | 585 | 0.0371 |
| room_0 | prior_full | 9 | sofa | replica_room_0_obj_9 | 47762 | 47762 | 1.0000 | 43896 | 0.9191 | 19672 | 0.4119 |
| room_0 | prior_full | 77 | sofa | replica_room_0_obj_77 | 53683 | 53683 | 1.0000 | 48059 | 0.8952 | 21166 | 0.3943 |
| room_0 | prior_full | 74 | chair | replica_room_0_obj_74 | 34054 | 34054 | 1.0000 | 30297 | 0.8897 | 16050 | 0.4713 |
| office_0 | prior_full | 9 | sofa | replica_office_0_obj_9 | 45382 | 45382 | 1.0000 | 36962 | 0.8145 | 11446 | 0.2522 |
| office_0 | prior_full | 7 | sofa | replica_office_0_obj_7 | 35493 | 35493 | 1.0000 | 18071 | 0.5091 | 4642 | 0.1308 |
| office_0 | prior_full | 58 | table | replica_office_0_obj_58 | 32030 | 32030 | 1.0000 | 26097 | 0.8148 | 9604 | 0.2998 |
| office_0 | prior_full | 61 | chair | replica_office_0_obj_61 | 43916 | 43916 | 1.0000 | 37943 | 0.8640 | 19674 | 0.4480 |
| room_0 | prior_100k | 6 | lamp | replica_room_0_obj_6 | 15786 | 10434 | 0.6610 | 1790 | 0.1716 | 503 | 0.0482 |
| room_0 | prior_100k | 9 | sofa | replica_room_0_obj_9 | 47762 | 31571 | 0.6610 | 28630 | 0.9068 | 14590 | 0.4621 |
| room_0 | prior_100k | 77 | sofa | replica_room_0_obj_77 | 53683 | 35485 | 0.6610 | 31580 | 0.8900 | 15665 | 0.4415 |
| room_0 | prior_100k | 74 | chair | replica_room_0_obj_74 | 34054 | 22510 | 0.6610 | 20360 | 0.9045 | 13516 | 0.6004 |
| office_0 | prior_100k | 9 | sofa | replica_office_0_obj_9 | 45382 | 28939 | 0.6377 | 23688 | 0.8185 | 8948 | 0.3092 |
| office_0 | prior_100k | 7 | sofa | replica_office_0_obj_7 | 35493 | 22633 | 0.6377 | 11893 | 0.5255 | 4125 | 0.1823 |
| office_0 | prior_100k | 58 | table | replica_office_0_obj_58 | 32030 | 20424 | 0.6377 | 16468 | 0.8063 | 7160 | 0.3506 |
| office_0 | prior_100k | 61 | chair | replica_office_0_obj_61 | 43916 | 28004 | 0.6377 | 23728 | 0.8473 | 14375 | 0.5133 |
| room_0 | prior_25k | 6 | lamp | replica_room_0_obj_6 | 15786 | 2609 | 0.1653 | 795 | 0.3047 | 141 | 0.0540 |
| room_0 | prior_25k | 9 | sofa | replica_room_0_obj_9 | 47762 | 7893 | 0.1653 | 7234 | 0.9165 | 4788 | 0.6066 |
| room_0 | prior_25k | 77 | sofa | replica_room_0_obj_77 | 53683 | 8871 | 0.1652 | 7961 | 0.8974 | 4930 | 0.5557 |
| room_0 | prior_25k | 74 | chair | replica_room_0_obj_74 | 34054 | 5627 | 0.1652 | 5271 | 0.9367 | 3959 | 0.7036 |
| office_0 | prior_25k | 9 | sofa | replica_office_0_obj_9 | 45382 | 7235 | 0.1594 | 6253 | 0.8643 | 3034 | 0.4194 |
| office_0 | prior_25k | 7 | sofa | replica_office_0_obj_7 | 35493 | 5658 | 0.1594 | 3625 | 0.6407 | 1491 | 0.2635 |
| office_0 | prior_25k | 58 | table | replica_office_0_obj_58 | 32030 | 5106 | 0.1594 | 4356 | 0.8531 | 2271 | 0.4448 |
| office_0 | prior_25k | 61 | chair | replica_office_0_obj_61 | 43916 | 7001 | 0.1594 | 6340 | 0.9056 | 4648 | 0.6639 |
| room_0 | prior_25k_full_none | 6 | lamp | replica_room_0_obj_6 | 15786 | 2609 | 0.1653 | 707 | 0.2710 | 412 | 0.1579 |
| room_0 | prior_25k_full_none | 9 | sofa | replica_room_0_obj_9 | 47762 | 7893 | 0.1653 | 7158 | 0.9069 | 5066 | 0.6418 |
| room_0 | prior_25k_full_none | 77 | sofa | replica_room_0_obj_77 | 53683 | 8871 | 0.1652 | 7927 | 0.8936 | 4829 | 0.5444 |
| room_0 | prior_25k_full_none | 74 | chair | replica_room_0_obj_74 | 34054 | 5627 | 0.1652 | 5269 | 0.9364 | 4311 | 0.7661 |
| office_0 | prior_25k_full_none | 9 | sofa | replica_office_0_obj_9 | 45382 | 7235 | 0.1594 | 6163 | 0.8518 | 3231 | 0.4466 |
| office_0 | prior_25k_full_none | 7 | sofa | replica_office_0_obj_7 | 35493 | 5658 | 0.1594 | 3717 | 0.6569 | 1536 | 0.2715 |
| office_0 | prior_25k_full_none | 58 | table | replica_office_0_obj_58 | 32030 | 5106 | 0.1594 | 4272 | 0.8367 | 2389 | 0.4679 |
| office_0 | prior_25k_full_none | 61 | chair | replica_office_0_obj_61 | 43916 | 7001 | 0.1594 | 6347 | 0.9066 | 5036 | 0.7193 |
| room_0 | prior_50k | 6 | lamp | replica_room_0_obj_6 | 15786 | 5217 | 0.3305 | 1102 | 0.2112 | 156 | 0.0299 |
| room_0 | prior_50k | 9 | sofa | replica_room_0_obj_9 | 47762 | 15786 | 0.3305 | 14212 | 0.9003 | 8134 | 0.5153 |
| room_0 | prior_50k | 77 | sofa | replica_room_0_obj_77 | 53683 | 17742 | 0.3305 | 16052 | 0.9047 | 9070 | 0.5112 |
| room_0 | prior_50k | 74 | chair | replica_room_0_obj_74 | 34054 | 11255 | 0.3305 | 10361 | 0.9206 | 6968 | 0.6191 |
| office_0 | prior_50k | 9 | sofa | replica_office_0_obj_9 | 45382 | 14469 | 0.3188 | 12417 | 0.8582 | 5297 | 0.3661 |
| office_0 | prior_50k | 7 | sofa | replica_office_0_obj_7 | 35493 | 11317 | 0.3189 | 6748 | 0.5963 | 2754 | 0.2434 |
| office_0 | prior_50k | 58 | table | replica_office_0_obj_58 | 32030 | 10212 | 0.3188 | 8489 | 0.8313 | 4288 | 0.4199 |
| office_0 | prior_50k | 61 | chair | replica_office_0_obj_61 | 43916 | 14002 | 0.3188 | 12281 | 0.8771 | 8544 | 0.6102 |
| room_0 | prior_75k | 6 | lamp | replica_room_0_obj_6 | 15786 | 7826 | 0.4958 | 1649 | 0.2107 | 494 | 0.0631 |
| room_0 | prior_75k | 9 | sofa | replica_room_0_obj_9 | 47762 | 23678 | 0.4957 | 21357 | 0.9020 | 12311 | 0.5199 |
| room_0 | prior_75k | 77 | sofa | replica_room_0_obj_77 | 53683 | 26614 | 0.4958 | 24023 | 0.9026 | 12519 | 0.4704 |
| room_0 | prior_75k | 74 | chair | replica_room_0_obj_74 | 34054 | 16882 | 0.4957 | 15420 | 0.9134 | 9911 | 0.5871 |
| office_0 | prior_75k | 9 | sofa | replica_office_0_obj_9 | 45382 | 21704 | 0.4783 | 17923 | 0.8258 | 7136 | 0.3288 |
| office_0 | prior_75k | 7 | sofa | replica_office_0_obj_7 | 35493 | 16975 | 0.4783 | 9182 | 0.5409 | 3650 | 0.2150 |
| office_0 | prior_75k | 58 | table | replica_office_0_obj_58 | 32030 | 15318 | 0.4782 | 12539 | 0.8186 | 5880 | 0.3839 |
| office_0 | prior_75k | 61 | chair | replica_office_0_obj_61 | 43916 | 21003 | 0.4783 | 17622 | 0.8390 | 11772 | 0.5605 |
| room_0 | prior_100k_geo | 6 | lamp | replica_room_0_obj_6 | 15786 | 10434 | 0.6610 | 801 | 0.0768 | 509 | 0.0488 |
| room_0 | prior_100k_geo | 9 | sofa | replica_room_0_obj_9 | 47762 | 31571 | 0.6610 | 28075 | 0.8893 | 18832 | 0.5965 |
| room_0 | prior_100k_geo | 77 | sofa | replica_room_0_obj_77 | 53683 | 35485 | 0.6610 | 31851 | 0.8976 | 22339 | 0.6295 |
| room_0 | prior_100k_geo | 74 | chair | replica_room_0_obj_74 | 34054 | 22510 | 0.6610 | 18420 | 0.8183 | 12873 | 0.5719 |
| office_0 | prior_100k_geo | 9 | sofa | replica_office_0_obj_9 | 45382 | 28939 | 0.6377 | 17075 | 0.5900 | 10459 | 0.3614 |
| office_0 | prior_100k_geo | 7 | sofa | replica_office_0_obj_7 | 35493 | 22633 | 0.6377 | 7494 | 0.3311 | 4649 | 0.2054 |
| office_0 | prior_100k_geo | 58 | table | replica_office_0_obj_58 | 32030 | 20424 | 0.6377 | 13955 | 0.6833 | 10361 | 0.5073 |
| office_0 | prior_100k_geo | 61 | chair | replica_office_0_obj_61 | 43916 | 28004 | 0.6377 | 17581 | 0.6278 | 8143 | 0.2908 |
| room_0 | prior_50k_geo | 6 | lamp | replica_room_0_obj_6 | 15786 | 5217 | 0.3305 | 1048 | 0.2009 | 646 | 0.1238 |
| room_0 | prior_50k_geo | 9 | sofa | replica_room_0_obj_9 | 47762 | 15786 | 0.3305 | 14392 | 0.9117 | 10747 | 0.6808 |
| room_0 | prior_50k_geo | 77 | sofa | replica_room_0_obj_77 | 53683 | 17742 | 0.3305 | 16477 | 0.9287 | 12141 | 0.6843 |
| room_0 | prior_50k_geo | 74 | chair | replica_room_0_obj_74 | 34054 | 11255 | 0.3305 | 9887 | 0.8785 | 7339 | 0.6521 |
| office_0 | prior_50k_geo | 9 | sofa | replica_office_0_obj_9 | 45382 | 14469 | 0.3188 | 10005 | 0.6915 | 7644 | 0.5283 |
| office_0 | prior_50k_geo | 7 | sofa | replica_office_0_obj_7 | 35493 | 11317 | 0.3189 | 5183 | 0.4580 | 3284 | 0.2902 |
| office_0 | prior_50k_geo | 58 | table | replica_office_0_obj_58 | 32030 | 10212 | 0.3188 | 7987 | 0.7821 | 6469 | 0.6335 |
| office_0 | prior_50k_geo | 61 | chair | replica_office_0_obj_61 | 43916 | 14002 | 0.3188 | 10609 | 0.7577 | 6969 | 0.4977 |


# Replica Gaussian-Direct Phase 5 Surface RGB

- Date: 2026-03-24
- Dataset family: `surface_rgb_roomwide_v2_384`
- Scenes: `room_0`, `office_0`
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

## Notes

- `room_0` baseline absolute final PSNR: 46.6062; baseline 3000-iter target PSNR: 42.2405
- `office_0` baseline absolute final PSNR: 44.2005; baseline 3000-iter target PSNR: 34.1250
- 해석은 absolute 값과 함께 scene별 baseline 대비 delta를 우선 본다.

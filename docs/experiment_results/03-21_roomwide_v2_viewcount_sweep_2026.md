# Replica Gaussian-Direct Room-Wide V2 View Count Sweep

- 기준 iteration: family baseline `3000` checkpoint PSNR
- 비교 범위: legacy biased room-wide vs room-wide v2
- protection 비교: `none`, `weak(0.02)`

## Legacy 96 vs V2 96

| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 | target_visible_min | target_visible_max |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_96_15000 | room_0 | none | 10.636681 | 164.459670 | 822.298352480866 | 12.750842094421387 | 0.6569922566413879 | 0.27862364053726196 | 100000 | 1251144 | 6620267 | n/a | n/a | 13 | 96 |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_96_15000 | office_0 | none | 10.896714 | 185.006414 | 925.0320701962337 | 12.845597267150879 | 0.6627061367034912 | 0.2716934382915497 | 100000 | 1489016 | 7356999 | n/a | n/a | 12 | 96 |
| gaussian_direct_same_scene_exact_clip_roomwide_96_15000 | room_0 | none | 10.636681 | 172.312989 | 861.5649450710043 | 12.676811218261719 | 0.6523940563201904 | 0.2815760672092438 | 200000 | 1400539 | 6754719 | 99695 | 76524 | 13 | 96 |
| gaussian_direct_same_scene_exact_clip_roomwide_96_15000 | office_0 | none | 10.896714 | 194.761033 | 973.8051648740657 | 12.783549308776855 | 0.6581193804740906 | 0.2732996642589569 | 200000 | 1658791 | 7575415 | 99453 | 69308 | 12 | 96 |
| gaussian_direct_same_scene_exact_clip_roomwide_96_weak_15000 | room_0 | weak(0.02) | 10.636681 | 274.747669 | 824.2430069921538 | 12.625554084777832 | 0.6473383903503418 | 0.2865156829357147 | 200000 | 1241274 | 6179662 | 100000 | 100000 | 13 | 96 |
| gaussian_direct_same_scene_exact_clip_roomwide_96_weak_15000 | office_0 | weak(0.02) | 10.896714 | 187.290186 | 936.4509291690774 | 12.835457801818848 | 0.6626927256584167 | 0.2719211280345917 | 200000 | 1493888 | 7039486 | 100000 | 100000 | 12 | 96 |

| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 | target_visible_min | target_visible_max |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_v2_96_15000 | room_0 | none | 10.466401 | 142.576012 | 712.8800623910502 | 12.371344566345215 | 0.6352410912513733 | 0.2857426106929779 | 100000 | 1130984 | 5067251 | n/a | n/a | 44 | 96 |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_v2_96_15000 | office_0 | none | 10.362615 | 161.904288 | 809.5214416370727 | 12.327751159667969 | 0.6244943737983704 | 0.29667437076568604 | 100000 | 1452309 | 5832220 | n/a | n/a | 70 | 96 |
| gaussian_direct_same_scene_exact_clip_roomwide_v2_96_15000 | room_0 | none | 10.466401 | 149.390296 | 746.9514775509015 | 12.392768859863281 | 0.6372739672660828 | 0.28643283247947693 | 200000 | 1240271 | 5171670 | 98315 | 72751 | 44 | 96 |
| gaussian_direct_same_scene_exact_clip_roomwide_v2_96_15000 | office_0 | none | 10.362615 | 166.351881 | 831.7594043542631 | 12.38895320892334 | 0.6282992362976074 | 0.2995295822620392 | 200000 | 1587933 | 5907118 | 99828 | 80439 | 70 | 96 |
| gaussian_direct_same_scene_exact_clip_roomwide_v2_96_weak_15000 | room_0 | weak(0.02) | 10.466401 | 143.404537 | 717.0226867338642 | 12.23788070678711 | 0.6246895790100098 | 0.29369011521339417 | 200000 | 1149437 | 4734791 | 100000 | 100000 | 44 | 96 |
| gaussian_direct_same_scene_exact_clip_roomwide_v2_96_weak_15000 | office_0 | weak(0.02) | 10.362615 | 157.369263 | 786.8463167180307 | 12.337276458740234 | 0.6255167126655579 | 0.2988491952419281 | 200000 | 1481470 | 5434169 | 100000 | 100000 | 70 | 96 |

## Legacy 192 vs V2 192

| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 | target_visible_min | target_visible_max |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_192_15000 | room_0 | none | 10.671445 | 158.005270 | 790.0263487612829 | 12.459938049316406 | 0.6297723650932312 | 0.29019418358802795 | 100000 | 1295519 | 5834238 | n/a | n/a | 46 | 192 |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_192_15000 | office_0 | none | 10.484012 | 181.454616 | 907.2730799857527 | 12.502394676208496 | 0.6372576951980591 | 0.287590354681015 | 100000 | 1414304 | 7067895 | n/a | n/a | 38 | 192 |
| gaussian_direct_same_scene_exact_clip_roomwide_192_15000 | room_0 | none | 10.671445 | 165.169745 | 825.8487236681394 | 12.47243595123291 | 0.6305935382843018 | 0.2903132736682892 | 200000 | 1435727 | 5938796 | 99590 | 76775 | 46 | 192 |
| gaussian_direct_same_scene_exact_clip_roomwide_192_15000 | office_0 | none | 10.484012 | 190.238290 | 951.1914485367015 | 12.563517570495605 | 0.6428912878036499 | 0.2834465205669403 | 200000 | 1589005 | 7324143 | 99164 | 69042 | 38 | 192 |
| gaussian_direct_same_scene_exact_clip_roomwide_192_weak_15000 | room_0 | weak(0.02) | 10.671445 | 160.340774 | 801.703870289959 | 12.347142219543457 | 0.6206004619598389 | 0.2974429428577423 | 200000 | 1294229 | 5501906 | 100000 | 100000 | 46 | 192 |
| gaussian_direct_same_scene_exact_clip_roomwide_192_weak_15000 | office_0 | weak(0.02) | 10.484012 | 181.719728 | 908.5986412581988 | 12.48743724822998 | 0.6371920704841614 | 0.2869609594345093 | 200000 | 1448037 | 6682891 | 100000 | 100000 | 38 | 192 |

| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 | target_visible_min | target_visible_max |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_v2_192_15000 | room_0 | none | 10.533118 | 140.079389 | 700.3969431426376 | 12.422257423400879 | 0.6314848065376282 | 0.2906654477119446 | 100000 | 1120272 | 4837692 | n/a | n/a | 88 | 192 |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_v2_192_15000 | office_0 | none | 10.473563 | 158.897363 | 794.4868164202198 | 12.243370056152344 | 0.6161832213401794 | 0.3018514811992645 | 100000 | 1417536 | 5577422 | n/a | n/a | 132 | 192 |
| gaussian_direct_same_scene_exact_clip_roomwide_v2_192_15000 | room_0 | none | 10.533118 | 147.730542 | 738.6527101988904 | 12.37963581085205 | 0.6283686757087708 | 0.2916799485683441 | 200000 | 1256266 | 4962493 | 95902 | 67291 | 88 | 192 |
| gaussian_direct_same_scene_exact_clip_roomwide_v2_192_15000 | office_0 | none | 10.473563 | 273.713326 | 821.1399789489806 | 12.291518211364746 | 0.6174044013023376 | 0.2981715798377991 | 200000 | 1549480 | 5681116 | 99741 | 79472 | 132 | 192 |
| gaussian_direct_same_scene_exact_clip_roomwide_v2_192_weak_15000 | room_0 | weak(0.02) | 10.533118 | 234.807075 | 704.4212252530269 | 12.301994323730469 | 0.6225711703300476 | 0.29576027393341064 | 200000 | 1136773 | 4490927 | 100000 | 100000 | 88 | 192 |
| gaussian_direct_same_scene_exact_clip_roomwide_v2_192_weak_15000 | office_0 | weak(0.02) | 10.473563 | 260.996601 | 782.9898040038534 | 12.28315258026123 | 0.6182171702384949 | 0.3006240427494049 | 200000 | 1453044 | 5250630 | 100000 | 100000 | 132 | 192 |

## Legacy 384 vs V2 384

| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 | target_visible_min | target_visible_max |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_384_15000 | room_0 | none | 10.568237 | 160.942096 | 804.7104814262129 | 12.28219223022461 | 0.618870198726654 | 0.2949766218662262 | 100000 | 1321531 | 5519919 | n/a | n/a | 158 | 384 |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_384_15000 | office_0 | none | 10.173265 | 178.470948 | 892.3547409600578 | 12.08999252319336 | 0.609119713306427 | 0.31194618344306946 | 100000 | 1479462 | 6460656 | n/a | n/a | 124 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_384_15000 | room_0 | none | 10.568237 | 168.557215 | 842.7860753959976 | 12.325146675109863 | 0.6206886172294617 | 0.29368001222610474 | 200000 | 1464170 | 5686544 | 99243 | 74441 | 158 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_384_15000 | office_0 | none | 10.173265 | 187.978705 | 939.8935252879746 | 12.30894947052002 | 0.625828742980957 | 0.2971493899822235 | 200000 | 1636817 | 6850703 | 99172 | 71026 | 124 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_384_weak_15000 | room_0 | weak(0.02) | 10.568237 | 162.927219 | 814.6360936318524 | 12.244332313537598 | 0.6135476231575012 | 0.2995116710662842 | 200000 | 1325831 | 5228865 | 100000 | 100000 | 158 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_384_weak_15000 | office_0 | weak(0.02) | 10.173265 | 183.540522 | 917.7026084912941 | 12.183032035827637 | 0.6204885244369507 | 0.30146661400794983 | 200000 | 1558255 | 6401951 | 100000 | 100000 | 124 | 384 |

| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 | target_visible_min | target_visible_max |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_v2_384_15000 | room_0 | none | 10.324856 | 138.474951 | 692.3747557080351 | 12.233680725097656 | 0.6134687066078186 | 0.3009008467197418 | 100000 | 1098647 | 4569461 | n/a | n/a | 189 | 384 |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_v2_384_15000 | office_0 | none | 10.034465 | 157.788629 | 788.9431459181942 | 12.176647186279297 | 0.6087865233421326 | 0.3019076883792877 | 100000 | 1389776 | 5301088 | n/a | n/a | 250 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_v2_384_15000 | room_0 | none | 10.324856 | 142.970085 | 714.8504251777194 | 12.270485877990723 | 0.6155269145965576 | 0.29919958114624023 | 200000 | 1218554 | 4568764 | 94809 | 64287 | 189 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_v2_384_15000 | office_0 | none | 10.034465 | 164.145310 | 820.7265520109795 | 12.234070777893066 | 0.613388180732727 | 0.2996126115322113 | 200000 | 1577293 | 5444376 | 99547 | 77740 | 250 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_v2_384_weak_15000 | room_0 | weak(0.02) | 10.324856 | 138.792701 | 693.9635063000023 | 12.195068359375 | 0.6091688275337219 | 0.30320924520492554 | 200000 | 1120542 | 4200452 | 100000 | 100000 | 189 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_v2_384_weak_15000 | office_0 | weak(0.02) | 10.034465 | 157.066329 | 785.3316447040997 | 12.209762573242188 | 0.6115788817405701 | 0.3019566237926483 | 200000 | 1447674 | 5085434 | 100000 | 100000 | 250 | 384 |

## Camera Distribution

| family | scene | selection_mode | train_position_histogram | train_axis_counts |
|---|---|---|---|---|
| Legacy biased room-wide 96-view | room_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 96-view | office_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 96-view | room_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 96-view | office_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 96-view | room_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 96-view | office_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 192-view | room_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 192-view | office_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 192-view | room_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 192-view | office_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 192-view | room_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 192-view | office_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 384-view | room_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 384-view | office_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 384-view | room_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 384-view | office_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 384-view | room_0 | room_wide_diverse_azimuth | None | None |
| Legacy biased room-wide 384-view | office_0 | room_wide_diverse_azimuth | None | None |
| Room-wide v2 96-view | room_0 | room_wide_balanced_azimuth_v2 | [10, 10, 10, 10, 10, 10, 10, 10] | {'ns': 37, 'ew': 40, 'other': 3} |
| Room-wide v2 96-view | office_0 | room_wide_balanced_azimuth_v2 | [10, 10, 10, 10, 10, 10, 10, 10] | {'ns': 40, 'ew': 39, 'other': 1} |
| Room-wide v2 96-view | room_0 | room_wide_balanced_azimuth_v2 | [10, 10, 10, 10, 10, 10, 10, 10] | {'ns': 37, 'ew': 40, 'other': 3} |
| Room-wide v2 96-view | office_0 | room_wide_balanced_azimuth_v2 | [10, 10, 10, 10, 10, 10, 10, 10] | {'ns': 40, 'ew': 39, 'other': 1} |
| Room-wide v2 96-view | room_0 | room_wide_balanced_azimuth_v2 | [10, 10, 10, 10, 10, 10, 10, 10] | {'ns': 37, 'ew': 40, 'other': 3} |
| Room-wide v2 96-view | office_0 | room_wide_balanced_azimuth_v2 | [10, 10, 10, 10, 10, 10, 10, 10] | {'ns': 40, 'ew': 39, 'other': 1} |
| Room-wide v2 192-view | room_0 | room_wide_balanced_azimuth_v2 | [20, 20, 20, 20, 20, 20, 20, 20] | {'ns': 75, 'ew': 80, 'other': 5} |
| Room-wide v2 192-view | office_0 | room_wide_balanced_azimuth_v2 | [20, 20, 20, 20, 20, 20, 20, 20] | {'ns': 80, 'ew': 79, 'other': 1} |
| Room-wide v2 192-view | room_0 | room_wide_balanced_azimuth_v2 | [20, 20, 20, 20, 20, 20, 20, 20] | {'ns': 75, 'ew': 80, 'other': 5} |
| Room-wide v2 192-view | office_0 | room_wide_balanced_azimuth_v2 | [20, 20, 20, 20, 20, 20, 20, 20] | {'ns': 80, 'ew': 79, 'other': 1} |
| Room-wide v2 192-view | room_0 | room_wide_balanced_azimuth_v2 | [20, 20, 20, 20, 20, 20, 20, 20] | {'ns': 75, 'ew': 80, 'other': 5} |
| Room-wide v2 192-view | office_0 | room_wide_balanced_azimuth_v2 | [20, 20, 20, 20, 20, 20, 20, 20] | {'ns': 80, 'ew': 79, 'other': 1} |
| Room-wide v2 384-view | room_0 | room_wide_balanced_azimuth_v2 | [40, 40, 40, 40, 40, 40, 40, 40] | {'ns': 141, 'ew': 160, 'other': 19} |
| Room-wide v2 384-view | office_0 | room_wide_balanced_azimuth_v2 | [40, 40, 40, 40, 40, 40, 40, 40] | {'ns': 160, 'ew': 151, 'other': 9} |
| Room-wide v2 384-view | room_0 | room_wide_balanced_azimuth_v2 | [40, 40, 40, 40, 40, 40, 40, 40] | {'ns': 141, 'ew': 160, 'other': 19} |
| Room-wide v2 384-view | office_0 | room_wide_balanced_azimuth_v2 | [40, 40, 40, 40, 40, 40, 40, 40] | {'ns': 160, 'ew': 151, 'other': 9} |
| Room-wide v2 384-view | room_0 | room_wide_balanced_azimuth_v2 | [40, 40, 40, 40, 40, 40, 40, 40] | {'ns': 141, 'ew': 160, 'other': 19} |
| Room-wide v2 384-view | office_0 | room_wide_balanced_azimuth_v2 | [40, 40, 40, 40, 40, 40, 40, 40] | {'ns': 160, 'ew': 151, 'other': 9} |

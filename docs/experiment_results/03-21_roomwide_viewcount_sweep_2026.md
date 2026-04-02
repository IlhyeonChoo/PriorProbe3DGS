# Replica Gaussian-Direct Legacy Biased Room-Wide View Count Sweep

- 이 문서는 기존 편향된 `legacy_biased_roomwide_{96,192,384}` 결과를 기록한 문서다.
- `roomwide_v2_*` 재실험 결과는 별도 보고서에서 legacy와 함께 비교한다.

- 기준 iteration: family baseline `3000` checkpoint PSNR
- 비교 범위: room-wide 96-view, 192-view, 384-view
- protection 비교: `none`, `weak(0.02)`

## Room-wide 96-view

| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 | target_visible_min | target_visible_max |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_96_15000 | room_0 | none | 10.636681 | 164.459670 | 822.298352480866 | 12.750842094421387 | 0.6569922566413879 | 0.27862364053726196 | 100000 | 1251144 | 6620267 | n/a | n/a | 13 | 96 |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_96_15000 | office_0 | none | 10.896714 | 185.006414 | 925.0320701962337 | 12.845597267150879 | 0.6627061367034912 | 0.2716934382915497 | 100000 | 1489016 | 7356999 | n/a | n/a | 12 | 96 |
| gaussian_direct_same_scene_exact_clip_roomwide_96_15000 | room_0 | none | 10.636681 | 172.312989 | 861.5649450710043 | 12.676811218261719 | 0.6523940563201904 | 0.2815760672092438 | 200000 | 1400539 | 6754719 | 99695 | 76524 | 13 | 96 |
| gaussian_direct_same_scene_exact_clip_roomwide_96_15000 | office_0 | none | 10.896714 | 194.761033 | 973.8051648740657 | 12.783549308776855 | 0.6581193804740906 | 0.2732996642589569 | 200000 | 1658791 | 7575415 | 99453 | 69308 | 12 | 96 |
| gaussian_direct_same_scene_exact_clip_roomwide_96_weak_15000 | room_0 | weak(0.02) | 10.636681 | 274.747669 | 824.2430069921538 | 12.625554084777832 | 0.6473383903503418 | 0.2865156829357147 | 200000 | 1241274 | 6179662 | 100000 | 100000 | 13 | 96 |
| gaussian_direct_same_scene_exact_clip_roomwide_96_weak_15000 | office_0 | weak(0.02) | 10.896714 | 187.290186 | 936.4509291690774 | 12.835457801818848 | 0.6626927256584167 | 0.2719211280345917 | 200000 | 1493888 | 7039486 | 100000 | 100000 | 12 | 96 |

## Room-wide 192-view

| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 | target_visible_min | target_visible_max |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_192_15000 | room_0 | none | 10.671445 | 158.005270 | 790.0263487612829 | 12.459938049316406 | 0.6297723650932312 | 0.29019418358802795 | 100000 | 1295519 | 5834238 | n/a | n/a | 46 | 192 |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_192_15000 | office_0 | none | 10.484012 | 181.454616 | 907.2730799857527 | 12.502394676208496 | 0.6372576951980591 | 0.287590354681015 | 100000 | 1414304 | 7067895 | n/a | n/a | 38 | 192 |
| gaussian_direct_same_scene_exact_clip_roomwide_192_15000 | room_0 | none | 10.671445 | 165.169745 | 825.8487236681394 | 12.47243595123291 | 0.6305935382843018 | 0.2903132736682892 | 200000 | 1435727 | 5938796 | 99590 | 76775 | 46 | 192 |
| gaussian_direct_same_scene_exact_clip_roomwide_192_15000 | office_0 | none | 10.484012 | 190.238290 | 951.1914485367015 | 12.563517570495605 | 0.6428912878036499 | 0.2834465205669403 | 200000 | 1589005 | 7324143 | 99164 | 69042 | 38 | 192 |
| gaussian_direct_same_scene_exact_clip_roomwide_192_weak_15000 | room_0 | weak(0.02) | 10.671445 | 160.340774 | 801.703870289959 | 12.347142219543457 | 0.6206004619598389 | 0.2974429428577423 | 200000 | 1294229 | 5501906 | 100000 | 100000 | 46 | 192 |
| gaussian_direct_same_scene_exact_clip_roomwide_192_weak_15000 | office_0 | weak(0.02) | 10.484012 | 181.719728 | 908.5986412581988 | 12.48743724822998 | 0.6371920704841614 | 0.2869609594345093 | 200000 | 1448037 | 6682891 | 100000 | 100000 | 38 | 192 |

## Room-wide 384-view

| experiment | scene | protection | target_psnr | time_to_target_sec | total_time_sec | psnr@15000 | ssim@15000 | lpips@15000 | gaussians@0 | gaussians@3000 | gaussians@15000 | protected@3000 | protected@15000 | target_visible_min | target_visible_max |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_384_15000 | room_0 | none | 10.568237 | 160.942096 | 804.7104814262129 | 12.28219223022461 | 0.618870198726654 | 0.2949766218662262 | 100000 | 1321531 | 5519919 | n/a | n/a | 158 | 384 |
| gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_roomwide_384_15000 | office_0 | none | 10.173265 | 178.470948 | 892.3547409600578 | 12.08999252319336 | 0.609119713306427 | 0.31194618344306946 | 100000 | 1479462 | 6460656 | n/a | n/a | 124 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_384_15000 | room_0 | none | 10.568237 | 168.557215 | 842.7860753959976 | 12.325146675109863 | 0.6206886172294617 | 0.29368001222610474 | 200000 | 1464170 | 5686544 | 99243 | 74441 | 158 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_384_15000 | office_0 | none | 10.173265 | 187.978705 | 939.8935252879746 | 12.30894947052002 | 0.625828742980957 | 0.2971493899822235 | 200000 | 1636817 | 6850703 | 99172 | 71026 | 124 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_384_weak_15000 | room_0 | weak(0.02) | 10.568237 | 162.927219 | 814.6360936318524 | 12.244332313537598 | 0.6135476231575012 | 0.2995116710662842 | 200000 | 1325831 | 5228865 | 100000 | 100000 | 158 | 384 |
| gaussian_direct_same_scene_exact_clip_roomwide_384_weak_15000 | office_0 | weak(0.02) | 10.173265 | 183.540522 | 917.7026084912941 | 12.183032035827637 | 0.6204885244369507 | 0.30146661400794983 | 200000 | 1558255 | 6401951 | 100000 | 100000 | 124 | 384 |

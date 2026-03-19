# Replica Multi-Object CLIP Align-Fix (2026-03-18)

## Goal

기존 `multi-object + CLIP + merge-init` 실험에서 보였던 prior 오정렬을 geometry alignment bug로 보고, 아래 5가지를 적용했다.

1. prior canonical seed 생성
2. anisotropic scale 적용
3. floor anchor / floor snap 적용
4. 4-way yaw search 적용
5. collision-aware skip (`skip_on_bad_alignment`) 적용

이번 라운드는 retrieval backend를 바꾸지 않고, CLIP retrieval 결과를 그대로 사용한 채 삽입 정렬만 수정했다.

## Root Cause

기존 경로의 핵심 문제는 retrieval보다 transform policy였다.

- raw ShapeSplat prior는 원점 중심이 아니었는데, target OBB center로 바로 translation했다.
- isotropic scale 하나만 사용해서 elongated sofa/table/chair에서 축 비율이 무너졌다.
- canonical forward axis 검증 없이 target rotation을 그대로 사용했다.
- multi-object insertion에서 collision / outside-scene rejection이 없었다.

## Implementation

- raw `splat.ply`는 그대로 보존했다.
- 삽입 전용 point-cloud seed를 추가 생성했다.
  - `canonical_seed_center.ply`
  - `canonical_seed_floor.ply`
  - `canonical_metadata.json`
- 런타임에서는 raw gaussian 대신 canonical seed point cloud를 삽입에 사용했다.
- scale은 `target_sizes / prior_bbox_size`의 3축 anisotropic scale로 적용했다.
- floor-supported category(`chair`, `sofa`, `table`, `lamp`)는 floor anchor를 기본으로 썼다.
- yaw는 `0, 90, 180, 270`도를 모두 평가했다.
- `v2`에서는 모든 yaw 후보가 reject되면 해당 prior를 drop했다.

## Office_0 Alignment Debug

기존 사용자가 직접 확인한 failure는 `target9 sofa wall penetration`, `target58 table floor penetration`, `target61 chair misplacement`였다.

수정 전후를 수치로 보면:

| target | prior | old issue proxy | old | new v1 |
|---|---|---:|---:|---:|
| 9 | `sofa_0131` | outside-scene ratio | `0.0709` | `0.0` |
| 58 | `table_0230` | bottom delta vs target floor | `-0.3945 m` | `+0.0003 m` |
| 61 | `chair_0239` | bottom delta vs target floor | `+0.0418 m` | `-0.0005 m` |

참고:

- `target58`와 `target61`의 aligned prior AABB IoU는 `0.0576 -> 0.1089`로 증가했다.
- 이 값은 table이 floor 아래에서 제대로 올라오면서 생긴 부작용이라, 시각 비교는 viewer 기준으로 같이 봐야 한다.

Viewer:

- old CLIP: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_15000/office_0/inspection/viewer.html`
- alignfix v1: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_alignfix_v1_15000/office_0/inspection/viewer.html`
- alignfix v2: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_alignfix_v2_15000/office_0/inspection/viewer.html`

## Results

Time-to-target는 각 scene의 `baseline multi 15000`에서 `3000 iter` PSNR을 target으로 다시 계산했다.

### office_0

| experiment | PSNR | SSIM | LPIPS | time-to-target (s) | total time (s) |
|---|---:|---:|---:|---:|---:|
| baseline multi 15000 | `13.2911` | `0.5942` | `0.3393` | `89.6877` | `448.4384` |
| CLIP multi 15000 | `13.3070` | `0.5958` | `0.3385` | `153.3418` | `460.0254` |
| CLIP alignfix v1 15000 | `13.3746` | `0.6100` | `0.3256` | `94.2125` | `471.0627` |
| CLIP alignfix v2 15000 | `13.3303` | `0.6044` | `0.3320` | `93.4865` | `467.4326` |

해석:

- alignment fix는 `office_0`에서 분명히 유효했다.
- 기존 CLIP 대비 final PSNR/SSIM/LPIPS가 모두 개선됐다.
- baseline 대비 speed gap도 `153.34s -> 94.21s / 93.49s`로 크게 줄었다.
- 다만 baseline 자체를 완전히 이기지는 못했다.

### room_0

| experiment | PSNR | SSIM | LPIPS | time-to-target (s) | total time (s) |
|---|---:|---:|---:|---:|---:|
| baseline multi 15000 | `13.6677` | `0.6604` | `0.2802` | `84.4107` | `422.0537` |
| CLIP multi 15000 | `13.7153` | `0.6676` | `0.2751` | `88.1886` | `440.9428` |
| CLIP alignfix v1 15000 | `13.7004` | `0.6660` | `0.2737` | `88.5037` | `442.5183` |
| CLIP alignfix v2 15000 | `13.6638` | `0.6608` | `0.2788` | `144.4169` | `433.2506` |

해석:

- `room_0`에서는 alignfix가 일관된 이득을 주지 못했다.
- `v1`은 old CLIP과 거의 비슷했고, `v2`는 더 나빠졌다.
- `v2`가 나빠진 직접 원인은 aggressive skip이었다.

`room_0 v2` dropped priors:

- target `6` -> `lamp_0085`, reason=`all_candidates_rejected`
- target `9` -> `sofa_0131`, reason=`all_candidates_rejected`

candidate debug:

- `outputs/experiments/oracle_prior_vanilla_3dgs_multi_clip_alignfix_v2_15000/room_0/alignment_candidates_6_00.json`
- `outputs/experiments/oracle_prior_vanilla_3dgs_multi_clip_alignfix_v2_15000/room_0/alignment_candidates_9_01.json`

이 둘은 모든 yaw 후보가 `outside_scene`로 reject됐다. 즉 `room_0`에서는 collision-aware skip 임계값이 너무 공격적이었다.

Viewer:

- alignfix v1: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_alignfix_v1_15000/room_0/inspection/viewer.html`
- alignfix v2: `outputs/backend_runs/oracle_prior_vanilla_3dgs_multi_clip_alignfix_v2_15000/room_0/inspection/viewer.html`

## Takeaways

- prior 오정렬은 실제 bug였고, `office_0`에서는 이걸 고치자 final quality와 time-to-target이 모두 개선됐다.
- 하지만 alignment fix만으로 항상 좋아지지는 않았다.
- `room_0`에서는 기존 CLIP path가 이미 괜찮았고, `v2`의 skip policy가 오히려 prior 수를 줄여서 성능을 깎았다.
- 따라서 다음 단계는 두 갈래로 가야 한다.
  - alignment fix는 유지
  - skip / collision threshold는 scene-adaptive 하게 완화하거나 soft weighting으로 바꾸기

## Domain Gap Note

현재 Replica 결과 저하의 한 원인 후보로, synthetic ShapeSplat CAD/object render prior와 Replica의 더 realistic indoor scene 사이 domain mismatch를 계속 유지한다.

다만 이번 라운드 결과를 보면, domain gap만이 아니라 **alignment bug**도 분명히 존재했다.  
추후 CAD 기반 synthetic indoor dataset을 확보한 뒤, 같은 align-fix pipeline을 다시 적용해서 domain-gap 가설을 별도로 검증한다.

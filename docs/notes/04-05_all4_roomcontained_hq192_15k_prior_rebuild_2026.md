# All-4 Roomcontained HQ192 15k Prior Rebuild Note

Date: 2026-04-05

관련 문서:
- `docs/notes/04-05_phase5_surface_prep_roomcontained_room0_2026.md`
- `docs/notes/04-05_sofa77_hq_prior_rebuild_2026.md`

---

## Summary

사용자 지시에 따라 room_0의 4개 target object prior를 전부 더 많은 학습 이미지와 더 많은 iteration으로 다시 생성했다.

사용자 의도 해석:
- "고품질로 새로 만든다" = object prior training dataset view 수를 크게 늘리고, training iteration도 늘린다

이번 재생성 설정:
- object total views: `192`
- object test views: `16`
- object train views: `176`
- prior train iterations: `15000`

기존 roomcontained prior 대비 변화:
- 기존: total `96`, train `80`, test `16`, iter `7000`
- 신규: total `192`, train `176`, test `16`, iter `15000`

즉 train image 수는 `80 -> 176`으로 약 `2.2x`, iteration은 `7000 -> 15000`으로 약 `2.14x` 증가했다.

---

## 실행 명령

- `uv run python scripts/prepare_replica_phase5_surface_assets.py --reference-dataset-config configs/datasets/replica_multi_roomwide_v2_384_shared.yaml --scene-id room_0 --scene-output-root /mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb_roomcontained_hq192 --dataset-config-out configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_roomcontained_hq192_shared.yaml --object-dataset-root /mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb_roomcontained_hq192 --prior-training-root outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-2026 --prior-stage-root outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-2026 --manifest-out outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-manifest-2026.json --config-out outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-2026.yaml --inventory-out outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-inventory-2026.json --report-out docs/notes/04-05_phase5_surface_prep_roomcontained_hq192_15k_2026.md --object-total-views 192 --object-test-views 16 --prior-train-iterations 15000 --overwrite`

---

## New artifacts

scene dataset root:
- `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb_roomcontained_hq192`

scene dataset config:
- `configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_roomcontained_hq192_shared.yaml`

object dataset root:
- `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb_roomcontained_hq192`

prior training root:
- `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-2026`

prior library root:
- `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-2026`

manifest:
- `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-manifest-2026.json`

config:
- `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-2026.yaml`

inventory:
- `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-hq192-15k-inventory-2026.json`

prep note:
- `docs/notes/04-05_phase5_surface_prep_roomcontained_hq192_15k_2026.md`

---

## Object-level outputs

### sofa 77
- object scene root:
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb_roomcontained_hq192/room_0/77`
- trained prior:
  - `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-2026/room_0/77/point_cloud/iteration_15000/point_cloud.ply`
- canonicalized prior:
  - `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-2026/room_0/77/canonicalized_floor_seed_frame.ply`
- runtime log final test PSNR:
  - `42.5217`

### chair 74
- object scene root:
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb_roomcontained_hq192/room_0/74`
- trained prior:
  - `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-2026/room_0/74/point_cloud/iteration_15000/point_cloud.ply`

### chair 73
- object scene root:
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb_roomcontained_hq192/room_0/73`
- trained prior:
  - `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-2026/room_0/73/point_cloud/iteration_15000/point_cloud.ply`

### table 11
- object scene root:
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb_roomcontained_hq192/room_0/11`
- trained prior:
  - `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-hq192-15k-2026/room_0/11/point_cloud/iteration_15000/point_cloud.ply`

---

## Current interpretation

이번 재생성으로 prior quality 측면의 가장 직접적인 요구사항은 반영되었다.
- 더 많은 training images
- 더 많은 training iterations
- 4개 object 전부 재생성

다만 이 문서는 builder 단계 완료 기록이다.
아직 이 새 HQ192/15k priors를 runtime insertion과 validator review에 연결해서 old priors와 직접 비교한 결과는 포함하지 않는다.

또한 edge background는 여전히 단순 grayscale gradient 기반이므로,
사용자 시각 기준의 edge 판단과 차이가 날 수 있는 문제는 별도로 남아 있다.

---

## Next recommended action

1. 새 HQ192/15k prior library를 사용한 room_0 iter0 smoke run을 별도 config로 생성
2. 기존 prior와 새 prior를 같은 조건에서 비교
3. edge extraction도 silhouette 친화적인 방식으로 보완 검토

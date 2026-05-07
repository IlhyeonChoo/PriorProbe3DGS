# Sofa77 HQ Prior Rebuild Note

Date: 2026-04-05

관련 문서:
- `docs/notes/04-05_phase5_surface_prep_roomcontained_room0_2026.md`
- `docs/notes/04-05_prior_position_fine_sweep_room0_100each_2026.md`

---

## Summary

사용자 피드백에 따라 `room_0`의 sofa(`obj_77`) prior를 기존 roomcontained 7k 버전 대신 더 높은 품질로 다시 생성했다.

이번 재생성 범위:
1. object surface dataset 재생성
2. object prior training을 `15000 iter`로 재실행
3. canonicalized gaussian asset 재생성
4. sofa77 전용 prior library / manifest / config 생성

현재 edge 표시 경로도 다시 확인했다.
- 현재 리뷰 이미지의 edge background는 `scripts/collect_prior_position_sweep.py::_image_edge_background()`의 단순 grayscale gradient 기반이다.
- 따라서 사람이 실제로 인지하는 edge와 다르게 잡힐 수 있다.
- 즉 sofa mismatch의 일부는 prior 자체 문제일 수 있고, 일부는 edge extraction path limitation일 수 있다.

---

## Code change

수정 파일:
- `scripts/prepare_replica_phase5_surface_assets.py`

변경 내용:
- `--target-object-id` 옵션 추가
- 특정 object만 선택적으로 rerender / retrain / restage 가능하도록 함

검증:
- `uv run python -m py_compile scripts/prepare_replica_phase5_surface_assets.py`
- 결과: 통과

의미:
- 전체 room_0 target set을 다시 만들지 않고도 sofa77만 builder 경로로 재생성 가능

---

## Rebuild command

실행 명령:
- `uv run python scripts/prepare_replica_phase5_surface_assets.py --reference-dataset-config configs/datasets/replica_multi_roomwide_v2_384_shared.yaml --scene-id room_0 --target-object-id 77 --scene-output-root /mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb_roomcontained_sofa77_hq --dataset-config-out configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_roomcontained_sofa77_hq_shared.yaml --object-dataset-root /mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb_roomcontained_sofa77_hq --prior-training-root outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-sofa77-15k-2026 --prior-stage-root outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-sofa77-15k-2026 --manifest-out outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-sofa77-15k-manifest-2026.json --config-out outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-sofa77-15k-2026.yaml --inventory-out outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-sofa77-15k-inventory-2026.json --report-out docs/notes/04-05_phase5_surface_prep_roomcontained_sofa77_15k_2026.md --prior-train-iterations 15000 --overwrite`

---

## New artifacts

scene dataset root:
- `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb_roomcontained_sofa77_hq`

scene dataset config:
- `configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_roomcontained_sofa77_hq_shared.yaml`

object dataset root:
- `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb_roomcontained_sofa77_hq`

prior training root:
- `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-sofa77-15k-2026`

final trained point cloud:
- `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-sofa77-15k-2026/room_0/77/point_cloud/iteration_15000/point_cloud.ply`

canonicalized seed-frame gaussian:
- `outputs/gaussian_direct/prior_training/04-05-surface-trained-roomcontained-sofa77-15k-2026/room_0/77/canonicalized_floor_seed_frame.ply`

prior stage root:
- `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-sofa77-15k-2026`

manifest:
- `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-sofa77-15k-manifest-2026.json`

config:
- `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-sofa77-15k-2026.yaml`

inventory:
- `outputs/gaussian_direct/prior_library/04-05-target-surface-roomcontained-sofa77-15k-inventory-2026.json`

prep note:
- `docs/notes/04-05_phase5_surface_prep_roomcontained_sofa77_15k_2026.md`

---

## Training evidence

runtime log 기준:
- object dataset views: `96`
- training iterations: `15000`
- final test PSNR at iter 15000: `42.5217`
- final train PSNR at iter 15000: `45.6518`

manifest 기준:
- library entry count: `1`
- object: `replica_room_0_obj_77`
- category: `sofa`
- render_count: `96`

즉 이번 재생성 결과물은 sofa77 전용 고품질 prior artifact다.

---

## Edge path current limitation

현재 edge background 생성 경로:
- `scripts/collect_prior_position_sweep.py`
  - `_image_edge_background()`

현재 방식:
- grayscale 변환
- x/y 1차 차분 기반 gradient magnitude
- quantile 정규화 후 edge background 생성

문제:
- 사람이 보는 semantic/texture edge와 다르게 잡힐 수 있음
- 내부 texture나 noise edge가 과하게 보일 수 있음
- object silhouette보다 배경 gradient가 더 강해질 수 있음

따라서 sofa 검토에서 사용자가 느낀
- "중간에 깨진 부분"
- "내 눈에 보이는 이미지와 다르게 edge가 잡힘"
은 builder 문제와 별도로 edge extraction 문제일 가능성이 있다.

---

## Next recommended action

1. 새 sofa77 HQ prior를 기존 validator/inspection 경로에 연결해 old sofa prior와 직접 비교
2. edge path는 단순 gradient 대신 더 보수적인 silhouette-friendly extraction으로 교체 검토
3. 이후 sofa77에 대해 iter0 validation 또는 targeted insertion smoke 재실행

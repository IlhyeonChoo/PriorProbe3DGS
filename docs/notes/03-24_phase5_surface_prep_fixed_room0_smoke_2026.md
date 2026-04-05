# Replica Phase 5 Surface Prep

## External Roots

- `DATA_STAGE_ROOT=/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs`
- `SURFACE_SCENE_DATASET_ROOT=${DATA_STAGE_ROOT}/replica_colmap_multi_roomwide_v2_384_surface_rgb`
- `SURFACE_OBJECT_DATASET_ROOT=${DATA_STAGE_ROOT}/replica_object_surface_exact_rgb`

## Summary

- Scene dataset root: `${SURFACE_SCENE_DATASET_ROOT}`
- Scene dataset config: `../../configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_shared.yaml`
- Prior object dataset root: `${SURFACE_OBJECT_DATASET_ROOT}`
- Prior training root: `../../outputs/gaussian_direct/prior_training/replica_surface_exact_trained_7000`
- Prior manifest: `../../outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip_fixed_room0_smoke_manifest.json`
- Prior config: `../../outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip_fixed_room0_smoke.yaml`

## Scenes

- `room_0`: 384 frames, 4 targets, renderer `pyrender_egl_vertex_color`

## Object Priors

- `${SURFACE_OBJECT_DATASET_ROOT}/room_0/6`: object `6` `lamp`, views 96, trained prior `../../outputs/gaussian_direct/prior_training/replica_surface_exact_trained_7000/room_0/6/point_cloud/iteration_7000/point_cloud.ply`
- `${SURFACE_OBJECT_DATASET_ROOT}/room_0/9`: object `9` `sofa`, views 96, trained prior `../../outputs/gaussian_direct/prior_training/replica_surface_exact_trained_7000/room_0/9/point_cloud/iteration_7000/point_cloud.ply`
- `${SURFACE_OBJECT_DATASET_ROOT}/room_0/77`: object `77` `sofa`, views 96, trained prior `../../outputs/gaussian_direct/prior_training/replica_surface_exact_trained_7000/room_0/77/point_cloud/iteration_7000/point_cloud.ply`
- `${SURFACE_OBJECT_DATASET_ROOT}/room_0/74`: object `74` `chair`, views 96, trained prior `../../outputs/gaussian_direct/prior_training/replica_surface_exact_trained_7000/room_0/74/point_cloud/iteration_7000/point_cloud.ply`

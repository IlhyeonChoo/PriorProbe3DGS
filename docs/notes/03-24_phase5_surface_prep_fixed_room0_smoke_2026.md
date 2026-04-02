# Replica Phase 5 Surface Prep

## Summary

- Scene dataset root: `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb`
- Scene dataset config: `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/configs/datasets/replica_multi_roomwide_v2_384_surface_rgb_shared.yaml`
- Prior object dataset root: `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb`
- Prior training root: `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/prior_training/replica_surface_exact_trained_7000`
- Prior manifest: `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip_fixed_room0_smoke_manifest.json`
- Prior config: `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/prior_library/replica_target_surface_exact_trained_clip_fixed_room0_smoke.yaml`

## Scenes

- `room_0`: 384 frames, 4 targets, renderer `pyrender_egl_vertex_color`

## Object Priors

- `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb/room_0/6`: object `6` `lamp`, views 96, trained prior `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/prior_training/replica_surface_exact_trained_7000/room_0/6/point_cloud/iteration_7000/point_cloud.ply`
- `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb/room_0/9`: object `9` `sofa`, views 96, trained prior `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/prior_training/replica_surface_exact_trained_7000/room_0/9/point_cloud/iteration_7000/point_cloud.ply`
- `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb/room_0/77`: object `77` `sofa`, views 96, trained prior `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/prior_training/replica_surface_exact_trained_7000/room_0/77/point_cloud/iteration_7000/point_cloud.ply`
- `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_object_surface_exact_rgb/room_0/74`: object `74` `chair`, views 96, trained prior `/home/ilhyeonchu/ReCompose3D/PriorProbe3DGS-gaussian/outputs/gaussian_direct/prior_training/replica_surface_exact_trained_7000/room_0/74/point_cloud/iteration_7000/point_cloud.ply`

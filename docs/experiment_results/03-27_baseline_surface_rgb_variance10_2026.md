# Replica Gaussian-Direct Surface RGB Baseline Variance (10 repeats, 2026-03-27)

## External Roots

- `DATA_STAGE_ROOT=/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs`
- `SURFACE_SCENE_DATASET_ROOT=${DATA_STAGE_ROOT}/replica_colmap_multi_roomwide_v2_384_surface_rgb`

## Scope

- Experiment family: `surface_rgb_baseline_15000_variance01~10`
- Dataset family: `replica_multi_roomwide_v2_384_surface_rgb_shared`
- Initialization: `from_scratch`
- Iterations: `15000`
- Scenes: `room_0`, `office_0`

## Same-Condition Check

- `room_0` source_path: `${SURFACE_SCENE_DATASET_ROOT}/room_0`
- `office_0` source_path: `${SURFACE_SCENE_DATASET_ROOT}/office_0`

## Summary

### room_0 (n=10)

- PSNR: mean `46.689600`, std `0.370861`, min `45.902729`, max `47.250519`, range `1.347790`
- SSIM: mean `0.992758`, std `0.000106`, min `0.992630`, max `0.992941`, range `0.000311`
- LPIPS: mean `0.023676`, std `0.000506`, min `0.022794`, max `0.024596`, range `0.001802`
- Total time: mean `160.703906s`, std `1.166435s`, min `159.216691s`, max `162.724392s`, range `3.507701s`

### office_0 (n=10)

- PSNR: mean `44.123923`, std `0.351150`, min `43.433895`, max `44.558788`, range `1.124893`
- SSIM: mean `0.988856`, std `0.001076`, min `0.987097`, max `0.990001`, range `0.002904`
- LPIPS: mean `0.029551`, std `0.002666`, min `0.026481`, max `0.034092`, range `0.007611`
- Total time: mean `161.714597s`, std `0.331722s`, min `161.010417s`, max `162.253877s`, range `1.243460s`

## Per-Run Values

### room_0

- `surface_rgb_baseline_15000_variance01`: PSNR `46.969055`, SSIM `0.992921`, LPIPS `0.023084`, total_time `160.054927s`
- `surface_rgb_baseline_15000_variance02`: PSNR `46.350323`, SSIM `0.992685`, LPIPS `0.023775`, total_time `162.291616s`
- `surface_rgb_baseline_15000_variance03`: PSNR `46.833569`, SSIM `0.992797`, LPIPS `0.023329`, total_time `160.017351s`
- `surface_rgb_baseline_15000_variance04`: PSNR `47.250519`, SSIM `0.992941`, LPIPS `0.022794`, total_time `160.692952s`
- `surface_rgb_baseline_15000_variance05`: PSNR `46.722424`, SSIM `0.992804`, LPIPS `0.023946`, total_time `159.504274s`
- `surface_rgb_baseline_15000_variance06`: PSNR `46.767612`, SSIM `0.992630`, LPIPS `0.023741`, total_time `162.724392s`
- `surface_rgb_baseline_15000_variance07`: PSNR `46.912449`, SSIM `0.992739`, LPIPS `0.024596`, total_time `159.216691s`
- `surface_rgb_baseline_15000_variance08`: PSNR `45.902729`, SSIM `0.992680`, LPIPS `0.023926`, total_time `160.737235s`
- `surface_rgb_baseline_15000_variance09`: PSNR `46.507401`, SSIM `0.992685`, LPIPS `0.023923`, total_time `161.614132s`
- `surface_rgb_baseline_15000_variance10`: PSNR `46.679916`, SSIM `0.992695`, LPIPS `0.023651`, total_time `160.185493s`

### office_0

- `surface_rgb_baseline_15000_variance01`: PSNR `43.868801`, SSIM `0.988187`, LPIPS `0.031669`, total_time `161.010417s`
- `surface_rgb_baseline_15000_variance02`: PSNR `44.244854`, SSIM `0.988757`, LPIPS `0.030029`, total_time `161.483934s`
- `surface_rgb_baseline_15000_variance03`: PSNR `44.165890`, SSIM `0.987176`, LPIPS `0.033214`, total_time `161.812115s`
- `surface_rgb_baseline_15000_variance04`: PSNR `44.409809`, SSIM `0.990001`, LPIPS `0.026481`, total_time `161.454780s`
- `surface_rgb_baseline_15000_variance05`: PSNR `43.740520`, SSIM `0.988828`, LPIPS `0.029668`, total_time `161.805641s`
- `surface_rgb_baseline_15000_variance06`: PSNR `43.433895`, SSIM `0.987097`, LPIPS `0.034092`, total_time `161.913494s`
- `surface_rgb_baseline_15000_variance07`: PSNR `44.253418`, SSIM `0.989980`, LPIPS `0.027691`, total_time `161.786606s`
- `surface_rgb_baseline_15000_variance08`: PSNR `44.097504`, SSIM `0.989511`, LPIPS `0.027522`, total_time `161.787882s`
- `surface_rgb_baseline_15000_variance09`: PSNR `44.465748`, SSIM `0.989811`, LPIPS `0.027137`, total_time `162.253877s`
- `surface_rgb_baseline_15000_variance10`: PSNR `44.558788`, SSIM `0.989211`, LPIPS `0.028008`, total_time `161.837228s`

## Interpretation

- This report uses only the fresh 10-run variance batch and excludes earlier legacy/current baseline runs.
- Small deltas below the measured baseline variance should not be treated as reliable evidence of improvement.

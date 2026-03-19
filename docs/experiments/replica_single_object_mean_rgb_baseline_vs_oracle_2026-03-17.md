# Replica Single-Object Mean_RGB Baseline vs Oracle

## Setup

- Dataset subset: target-centric Replica exports on SSD
- Scenes: `room_0`, `office_0`
- Reconstruction backend: vanilla 3DGS
- Prior library: ShapeSplat ModelNet chair subset, 256 candidates
- Retrieval feature: `mean_rgb`
- Oracle insertion mode: single object, top-1 same-category retrieval, merge-init

## Results

| scene | run | total_time_sec | psnr@3000 | psnr@7000 | ssim@7000 | lpips@7000 | prior |
|---|---|---:|---:|---:|---:|---:|---|
| room_0 | baseline | 118.7176 | 12.5689 | 13.0644 | 0.4940 | 0.4027 | - |
| room_0 | oracle | 121.3114 | 12.5759 | 13.0911 | 0.4968 | 0.4005 | chair_0201 |
| office_0 | baseline | 133.9288 | 12.2815 | 12.6235 | 0.4569 | 0.4583 | - |
| office_0 | oracle | 136.4333 | 12.3041 | 12.6543 | 0.4611 | 0.4547 | chair_0240 |

## Notes

- Mean_RGB single-object 결과의 원본 machine-readable 산출물은 `outputs/experiments/.../evaluation.json` 과 `outputs/reports/replica_oracle_vs_baseline_summary.json` 에 보관한다.
- 관찰 요약:
  - 최종 품질은 oracle이 소폭 높았다.
  - baseline 3000-iteration PSNR 기준 time-to-target은 oracle이 두 scene 모두 약간 느렸다.
  - 따라서 이 결과는 prior 삽입 자체보다 retrieval feature와 insertion coverage가 병목일 가능성을 시사한다.

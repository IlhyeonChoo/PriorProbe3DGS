# Gaussian-Direct Storage Cleanup (2026-03-21)

## Result PLY naming

- `point_cloud/iteration_<N>/` 아래에 보이는 두 이름은 실제 중복 저장이 아니다.
- 실제 데이터 파일은 `same_scene_exact_iter_3000.ply` 같은 새 규칙 파일 하나뿐이다.
- `point_cloud.ply`는 기존 평가/리포트/뷰어 스크립트 호환성을 위한 심볼릭 링크다.
- 전체 `outputs/gaussian_direct/backend_runs`를 점검한 결과, `point_cloud.ply`가 일반 파일로 중복 저장된 경우는 없었다.

## Why the symlink stays

다음 경로들이 여전히 `point_cloud.ply`를 직접 참조한다.

- `scripts/report_replica_gaussian_direct_upper_bound.py`
- `scripts/build_initial_snapshot_viewer.py`
- `src/priorprobe/evaluation/metrics.py`
- `scripts/run_experiment.py`

따라서 현재 구조에서는 `실제 named PLY 1개 + point_cloud.ply symlink 1개`가 가장 안전하다.

## Smoke artifact cleanup

- smoke 실험의 무거운 backend 산출물은 full run과 테스트가 이미 대체하고 있어서 계속 보관할 필요가 없다고 판단했다.
- `outputs/gaussian_direct/experiments/*smoke*` 아래의 lightweight metadata와 로그는 남겼다.
- 아래의 heavy backend run 디렉토리만 삭제했다.

```text
outputs/gaussian_direct/backend_runs/baseline_smoke_vanilla_3dgs
outputs/gaussian_direct/backend_runs/gaussian_direct_baseline_from_scratch_vanilla_3dgs_multi_smoke_1000
outputs/gaussian_direct/backend_runs/gaussian_direct_existing_clip_only_smoke_1000
outputs/gaussian_direct/backend_runs/gaussian_direct_merged_clip_retrieval_smoke_1000
outputs/gaussian_direct/backend_runs/gaussian_direct_merged_oracle_select_clip_smoke_1000
outputs/gaussian_direct/backend_runs/gaussian_direct_same_scene_exact_clip_diverse_384_freeze_smoke_1000
outputs/gaussian_direct/backend_runs/gaussian_direct_same_scene_exact_clip_diverse_384_weak_smoke_1000
outputs/gaussian_direct/backend_runs/gaussian_direct_same_scene_exact_clip_smoke_1000
```

- 정리 전 총 용량은 약 `5.11 GB`였다.
- smoke 결과의 수치 기록은 기존 markdown 보고서와 `outputs/gaussian_direct/experiments` 아래 metadata로 추적 가능하다.

## Backup directory cleanup

- `run_experiment.py`는 같은 실험 이름과 scene을 다시 실행하면 기존 결과를 덮어쓰지 않고 `*_backup_<timestamp>` 디렉토리로 옮긴다.
- 이번 정리에서는 같은 실험의 이전 시도를 보존하기 위한 backup 디렉토리도 모두 제거했다.
- 삭제 대상:
  - `outputs/gaussian_direct/experiments/*/*_backup_*`
  - `outputs/gaussian_direct/backend_runs/*/*_backup_*`
- 삭제 수량:
  - experiment backup `15개`
  - backend backup `3개`
- 정리 전 총 용량:
  - experiment backup 약 `1.9 MB`
  - backend backup 약 `7.99 GB`

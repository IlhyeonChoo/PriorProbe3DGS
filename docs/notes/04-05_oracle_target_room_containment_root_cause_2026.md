# Oracle Target Room-Containment Root Cause Note

Date: 2026-04-05

관련 문서:
- `docs/experiment_plans/04-04_prior_insertion_geometry_fix_plan_2026.md`
- `docs/notes/04-04_prior_insertion_geometry_phaseA_room0_2026.md`
- `docs/notes/03-24_phase5_surface_alignment_bug_2026.md`

---

## Summary

`room_0`의 lamp(obj_6), sofa(obj_9) prior geometry 오류는 prior affine transform 자체보다 upstream `oracle target` 선택 문제와 더 강하게 연결된다.

핵심 증거:
- 기존 `room_0` oracle targets는 volume 기준 top-4 선택으로 `6, 9, 77, 74`를 사용했다.
- 이 중
  - `obj_6` lamp는 room bbox 기준 target AABB outside ratio = `1.0`
  - `obj_9` sofa는 room bbox 기준 target AABB outside ratio ≈ `0.319`
- strict geometry validation smoke는 정확히 이 둘만 fail했다.

따라서 이번 repro의 root cause는
- `src/priorprobe/replica_export.py`의 `select_top_targets()`가 room containment 없이 semantic object를 volume 우선으로 고른 점
- surface RGB dataset이 reference roomwide_v2 oracle targets를 그대로 복사한 점
으로 좁혀진다.

---

## Evidence

### 1. 기존 top-4 current policy

raw semantic objects를 room containment 없이 volume 순으로 정렬하면:
- `6` lamp
- `9` sofa
- `77` sofa
- `74` chair

이는 기존 `oracle/targets.json`와 동일했다.

### 2. room bbox 대비 outside ratio

`room_0` room bbox 기준:
- `obj_6`: outside ratio = `1.0`
- `obj_9`: outside ratio ≈ `0.3188`
- `obj_77`: outside ratio ≈ `0.0023`
- `obj_74`: outside ratio ≈ `0.0`

즉 `obj_6`, `obj_9`는 room 내부 reconstruction target로 쓰기 부적절했다.

### 3. room-contained top-4

room containment(center inside + AABB outside ratio <= 0.01) 기준으로 다시 고르면:
- `77` sofa
- `74` chair
- `73` chair
- `11` table

---

## Code change

수정 파일:
- `src/priorprobe/replica_export.py`

변경 내용:
- `select_top_targets()`에 room containment 필터 추가
  - target center must be inside room bbox
  - target AABB outside ratio must be <= 0.01

테스트 추가:
- `tests/test_replica_export.py`
  - room 밖 큰 object가 volume이 커도 제외되는지 검증

검증:
- `tests/test_replica_export.py`
- `tests/test_vanilla_3dgs_backend.py`
- `tests/test_run_experiment_script.py`
- `tests/test_alignment_search.py`
- 결과: `25 passed`

---

## Oracle target regeneration

재생성 방식:
1. patched exporter로 `room_0` reference oracle scene을 임시 출력 경로에 재생성
2. 생성된 `target.json`, `targets.json`를 실제 dataset 경로에 백업 후 교체

실제 교체 대상:
- reference dataset
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384/room_0/oracle/target.json`
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384/room_0/oracle/targets.json`
- surface RGB dataset
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb/room_0/oracle/target.json`
  - `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_v2_384_surface_rgb/room_0/oracle/targets.json`

backup stamp:
- `20260405_060556`

재생성 후 `targets.json` object ids:
- `77`, `74`, `73`, `11`

---

## Remaining risk

- surface RGB dataset의 `oracle/objects/*/crops`는 새 target set(`73`, `11`) 기준으로 아직 재생성되지 않았다.
- 즉 현재는 target metadata는 갱신됐지만, surface object-only crop/render 및 same-scene prior training asset은 아직 기존 object set(`6`, `9`, `77`, `74`)에 머물 수 있다.
- 따라서 다음 단계는
  - surface RGB scene-side oracle object crops
  - object surface datasets
  - same-scene trained priors / prior library
를 새 target set 기준으로 재생성하는 것이다.

---

## Next recommended action

1. `room_0`에 대해 surface RGB object crop / object dataset / prior training을 새 target set(77,74,73,11) 기준으로 재생성
2. 이후 geometry validation smoke를 새 target set으로 다시 실행
3. 그 다음에야 prior insertion 성능 실험을 재개

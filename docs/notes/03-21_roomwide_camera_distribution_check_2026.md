# Room-Wide Camera Distribution Check

Date: 2026-03-21

## Summary

- 현재 `room_wide_diverse_azimuth` exporter는 이름과 달리 `room_0`, `office_0`에서 균등한 4방향 coverage를 만들지 못했다.
- 실제 `sparse/0/images.txt`와 `sparse/0/test.txt`를 기준으로 train camera 분포를 집계하면, 대부분의 view가 한 축의 정반대 2방향에 몰려 있다.
- 따라서 side wall을 보는 시점이 부족하고, 사용자가 관찰한 `iter 15000`에서 옆면 Gaussian이 약해지는 현상과 일관된다.
- 이 문서가 다루는 기존 `roomwide_{96,192,384}` family는 이후 모든 보고서에서 `legacy_biased_roomwide_{96,192,384}`로 표기한다.
- 후속 수정본은 `roomwide_v2_*`로 분리하며, `room_center`를 계속 보더라도 camera position azimuth가 특정 1-2개 bin에 과도하게 몰리지 않도록 다시 export한다.

## Evidence

### Room-Wide 192

- `room_0`
  - train position bins: `[71, 5, 0, 11, 21, 0, 5, 47]`
  - train forward bins: `[21, 0, 5, 47, 71, 5, 0, 11]`
  - train axis counts: `ew=149`, `ns=9`, `other=2`
- `office_0`
  - train position bins: `[1, 29, 104, 2, 5, 2, 16, 1]`
  - train forward bins: `[5, 2, 16, 1, 1, 29, 104, 2]`
  - train axis counts: `ns=151`, `ew=8`, `other=1`

### Room-Wide 384

- `room_0`
  - train axis counts: `ew=293`, `ns=24`, `other=3`
- `office_0`
  - train axis counts: `ns=279`, `ew=37`, `other=4`

### Room-Wide 96

- `room_0`
  - train axis counts: `ew=70`, `ns=9`, `other=1`
- `office_0`
  - train axis counts: `ns=76`, `ew=3`, `other=1`

## Why This Happened

- exporter는 camera position의 azimuth를 완전히 균등하게 강제하지 않는다.
- 모든 camera가 `room_center`를 바라보도록 고정되어 있어서, position이 한 축에 몰리면 forward direction도 그 반대 2방향으로 함께 몰린다.
- 현재 `scene_visible_ratio > 0` 조건과 candidate ranking이 결합되면서 valid candidate 자체가 한 축으로 편향됐다.

## External Roots

- `DATA_STAGE_ROOT=/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs`
- `ROOMWIDE_192_ROOT=${DATA_STAGE_ROOT}/replica_colmap_multi_roomwide_192`

## Relevant Code / Metadata

- selection and acceptance: [replica_export.py](../../src/priorprobe/replica_export.py#L966)
- test split assignment: [replica_export.py](../../src/priorprobe/replica_export.py#L1005)
- scene meta histogram write: [replica_export.py](../../src/priorprobe/replica_export.py#L1047)
- room_0 192 scene meta: [scene_meta.json](/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_192/room_0/scene_meta.json)
- office_0 192 scene meta: [scene_meta.json](/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi_roomwide_192/office_0/scene_meta.json)

## Conclusion

- 현재 room-wide dataset은 train 이미지가 "여러 방향"이라는 의미에서는 맞지만, "방 전체를 고르게 보는" dataset은 아니다.
- 사용자의 관찰대로 사실상 두 방향 축에서 본 이미지가 압도적으로 많다.
- 따라서 기존 room-wide 결과는 비교용 참고 자료로만 유지하고, 새 `roomwide_v2` 결과와 직접 구분해서 해석해야 한다.

# Replica Dense View Probe

- 목적: 현재 Replica reconstruction 입력이 실제로 데이터 부족인지, 아니면 export 설정이 보수적인지 확인한다.
- 기준 scene: `room_0`, `office_0`
- 현재 multi-object 실험 dataset root: `/mnt/3dgs-ssd/3dgs-stage/priorprobe3dgs/replica_colmap_multi`

## Existing Staging

- raw Replica root에는 18개 scene이 존재한다.
- 실제 학습 입력은 raw를 직접 읽지 않고, `images + sparse/0`를 갖춘 processed subset scene만 사용한다.
- 현재 multi-object gaussian-direct 실험은 `room_0`, `office_0` 두 scene만 stage돼 있고, 각 scene은 96장이다.
- 기존 결과 inventory는 [03-20_image_count_inventory_2026.md](../notes/03-20_image_count_inventory_2026.md)에 정리했다.

## Capacity Probe

- probe method:
  - raw Replica semantic mesh에서 현재 exporter와 동일한 `scene-centric multi-object` camera path를 생성한다.
  - 실제 PNG 저장은 하지 않고, candidate pose의 semantic visibility만 센다.
  - renderer는 현재 환경에서 `semantic_point_renderer` fallback을 사용했다.
- probe config:
  - categories: `chair`, `sofa`, `table`, `lamp`
  - max objects: `4`
  - candidate poses per scene: `4096`
  - width/height: `512 x 512`
  - hfov: `60`
  - point sample count: `200000`
  - visibility threshold reference: `0.15`

## Probe Result

| Scene | Positive Candidates | Candidates >= 0.15 | Mean Visible Ratio | P50 | P90 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `room_0` | `4096 / 4096` | `0 / 4096` | `0.031335` | `0.029091` | `0.046839` |
| `office_0` | `4096 / 4096` | `0 / 4096` | `0.046175` | `0.045574` | `0.052225` |

## Interpretation

- 현재 raw Replica가 부족한 것은 아니다. dense reconstruction 이미지는 raw에서 추가로 계속 export할 수 있다.
- 현재 exporter 규칙에서는 `positive visibility (> 0)`인 후보 pose가 매우 많다. 따라서 96장에서 192장, 384장, 그 이상으로 늘리는 것 자체는 dataset 용량 때문에 막히지 않는다.
- 반대로 `union visible ratio >= 0.15`인 강한 후보는 이번 probe에서 0개였다. 즉 현재 scene-centric path는 object가 화면에서 크게 보이는 dense view를 만드는 경로가 아니다.
- 현재 96장 export의 `scene_meta.json`도 `oracle_effective_min_visible_ratio: 0.0`을 기록하고 있다. 이미 기존 staging부터 강한 가시성 기준을 포기한 상태다.

## Practical Next Step

- reconstruction 입력 자체를 늘리는 목적이라면 다음 dense rung으로 `384 images` 정도는 바로 시도할 수 있다.
- 다만 dense 실험의 품질을 높이려면 이미지 수만 늘리는 것보다 아래를 같이 조정하는 게 좋다.
  - `scene-centric` 대신 wider room coverage path
  - visibility threshold와 radius 범위 재조정
  - train/test split을 더 큰 total view count에 맞게 재설계
- 즉 현재 결론은 `데이터가 없어서 못 늘리는 상황은 아니고, exporter policy를 어떻게 바꿀지가 핵심`이다.

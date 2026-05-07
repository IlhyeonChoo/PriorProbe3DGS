# Edge Metric 재설계 분석

Date: 2026-04-06

관련 문서:
- `docs/notes/04-06_double_sided_prior_rebuild_results_2026.md`

배경: sofa 77이 bbox_iou 0.81로 우수하지만 edge_distance 13.8px (threshold 12.0)로 항상 AMBIGUOUS 판정됨. Edge metric 측정 방식 자체 재검토 필요.

---

## 1. 현재 구현 현황

### 1.1 GT mask 생성 경로

- `src/priorprobe/validation/prior_position_validator.py:495` — `mask = np.asarray(semantic == int(obj_id), dtype=bool)`
- `prior_position_validator.py:496-497` — `apply_binary_closing`이 켜져 있으면 `_binary_closing(mask)` 한 번 적용
- `generate_gt_semantic_masks` (line 510-515)는 bundle을 감싸 `bundle.masks`만 반환, 추가 후처리 없음

GT semantic source:
- 주 경로: `ReplicaHabitatRenderer` — `src/priorprobe/replica_export.py:838-841`에서 `observations["semantic"]`를 그대로 복사
- Fallback: `ReplicaPointRenderer` — `replica_export.py:882-905`에서 sampled semantic points를 `np.rint`로 픽셀에 꽂아 채움

참고: Canny edge detection은 `scripts/collect_prior_position_sweep.py:145`에만 있고 line 158-161에서 overlay 배경용으로만 사용. **Metric 계산과 무관.**

### 1.2 Prior mask 생성 경로

- `prior_position_validator.py:681-692` — `render_full_prior_views`는 room scene가 아니라 `selected_priors`만 합친 GaussianModel을 렌더
- `prior_position_validator.py:701-721` — `render_isolated_prior_views`는 object별 prior만 따로 렌더
- `prior_position_validator.py:738-740` — `visible = isolated_candidate & (abs(isolated_depth - full_depth) <= epsilon)`로 visible prior mask 생성
- `_render_gaussian_model_views` line 636에서 `antialiasing=False`

**핵심**: 현재 edge/IoU/centroid가 보는 prior는 "scene-occluded silhouette"가 아니라 **prior-only rendered silhouette**. 지금의 edge noise는 splat raster와 binary contour 추출의 영향을 강하게 받음.

### 1.3 Edge metric 계산

`_symmetric_contour_chamfer` (line 811):
1. `_boundary_points`로 GT/prior mask 각각의 boundary 픽셀 추출 (`mask & ~erode(mask)`)
2. 두 contour 점집합 간 symmetric chamfer distance (평균) 계산
3. 양쪽 모두 2D mask boundary 기반

---

## 2. GT edge 측정 현황 점검

### 2.1 코드 레벨 관찰

**(a) Erosion structuring element**

- `_binary_erode` (line 449-455): `dy, dx in range(3)` 전체를 AND
- Structuring element는 4-connected cross가 아니라 **full 3x3 square**
- 즉 사실상 **8-neighborhood erosion**

**(b) GT mask는 hard binary label**

- Soft coverage, alpha, sub-pixel interpolation 없음
- Habitat 경로: 반환된 `semantic` 정수 배열을 바로 `== object_id`에 넣음
- Point-renderer fallback: `np.rint`와 단순 overwrite만 사용
- Habitat 내부 rasterizer의 sub-pixel 처리 여부는 `unverified hypothesis`

**(c) Binary closing의 영향**

- `_binary_closing` (line 458-459): `erode(dilate(mask))`, 같은 3x3 square
- 1px 구멍, 대각선 틈, 1px notch를 메우고 조각을 붙임
- 깨끗한 큰 실루엣에서는 대체로 외곽 유지
- **작은 concavity나 diagonal crack가 있으면 contour가 국소적으로 1px 바깥으로 밀릴 수 있음**
- 이후 `_boundary_points`가 `mask & ~eroded`를 쓰기 때문에, 얇은 부분은 boundary shell이 아니라 **그 얇은 구조 전체가 boundary**가 되기 쉬움

**(d) Boundary subsampling 왜곡**

- `_boundary_points` (line 801-807): boundary pixel 전부 수집 후 1024개 초과 시 `np.linspace`로 subsampling
- **Row-major order 기반 subsampling**
- Contour arc-length, curvature, component별 균형을 보지 않음
- Sofa armrest/backrest처럼 길고 얇은 형상은 총 boundary pixel이 많을 때 세부 윤곽이 과소대표될 수 있음

**(e) Fragmentation 처리의 맹점**

- 부분 가림으로 GT mask가 조각나면 boundary는 안정적이지 않음
- `_boundary_points`는 **외곽 실루엣만이 아니라 fragment의 모든 exposed perimeter와 hole boundary**를 다 포함
- Internal occlusion seam이 생기면 contour가 거기서도 늘어남
- **더 큰 문제**: line 874-878에서 fragment가 많으면 `gt_mask_low_confidence`만 표시하고, line 885와 909-913에서 edge distance와 median 집계에는 그대로 넣음
- 즉 seam explosion을 **"경고만 하고 점수에서는 계속 먹는" 구조**

### 2.2 구체적 약점 5가지

1. GT mask가 hard binary label이라 1px aliasing과 label stair-step이 contour에 그대로 반영됨
2. `apply_binary_closing`이 3x3 square 기반이라 작은 틈과 notch를 메우면서 contour를 국소적으로 1px 바깥으로 이동시킬 수 있음
3. `_boundary_points`가 outer silhouette만 보지 않고 internal seam과 hole boundary까지 전부 edge로 취급
4. `max_points=1024` subsampling이 contour-aware가 아니라 thin elongated geometry를 왜곡할 수 있음
5. GT fragmentation은 low-confidence로만 기록되고 배제되지 않으며, fallback `ReplicaPointRenderer`는 sample-density와 `np.rint` rounding까지 겹쳐 boundary 품질이 더 흔들릴 수 있음

### 2.3 개선 방향

**옵션 A (권장)**: 현재의 binary GT/prior mask representation은 유지한 채 outer silhouette만 뽑아 **distance-transform 기반 symmetric distance**를 계산
- 1024-point cap, row-order subsampling, internal seam 과민성이 한 번에 줄어듦

**옵션 B**: GT source 자체가 의심되는 경우 edge 평가를 mesh-backed semantic rasterizer 경로에만 허용하거나, `ReplicaPointRenderer` fallback 결과를 별도 quality tier로 분리해 threshold 해석을 다르게 가져감

---

## 3. Prior Gaussian Center 기반 Edge 제안 평가

### 3.1 장점

- Gaussian center를 직접 projection하면 splat fringe, alpha tail, raster stair-step 같은 2D splatting artifact를 크게 줄일 수 있음
- Learned anisotropy나 scale tail을 무시하고 보다 "geometric core"만 보게 되므로 mesh 기반 GT와 직관적으로 비교하기 쉬움
- bbox/centroid는 이미 괜찮고 edge만 문제인 케이스에서는, 지나치게 두꺼운 rendered silhouette 대신 더 얇은 geometric outline이 false penalty를 줄일 가능성

### 3.2 단점과 위험

- **가장 큰 문제**: metric unit mismatch. 지금 IoU/centroid는 rendered visible mask를 보는데, edge만 center-hull로 바꾸면 한 객체에 대해 **서로 다른 물체 표현**을 비교하게 됨
- **Depth occlusion 소실**: wall/floor 뒤 Gaussian, foreground 뒤에 숨은 Gaussian, 다른 prior 뒤 Gaussian까지 모두 2D에 투영됨
- Sofa처럼 concavity가 있는 형상은 convex hull이 과도하게 부풀고, 반대로 sparse center 분포에서는 alpha shape가 GT contour 안쪽으로 수축
- Low-opacity outlier Gaussian 몇 개가 바깥에 있으면 hull이 쉽게 inflated됨
- Multi-component prior, 팔걸이/등받이처럼 떨어진 군집, projected center가 거의 collinear한 degenerate view에서 contour 정의가 불안정

### 3.3 엄밀하게 구현하려면 필요한 부가 처리

- View frustum culling과 `z > 0` 검사, screen bounds clipping
- Opacity threshold나 contribution threshold (그렇지 않으면 거의 안 보이는 Gaussian도 hull을 키움)
- Full-scene depth와의 occlusion test (현재 코드에는 scene depth가 없으므로 visibility model부터 다시 설계 필요)
- Hull choice 결정: convex hull은 sofa에 너무 거칠고, alpha shape/concave hull은 alpha가 density와 view scale에 매우 민감
- Multi-component prior를 하나의 hull로 합칠지, component별 contour를 유지할지 규칙
- Projected point set가 3개 미만이거나 거의 일직선인 경우의 degenerate fallback

### 3.4 판정

Gaussian-center 기반 edge는 **주 metric replacement로는 부적절**.

Raster noise를 줄이고 싶다면 더 일관된 대안은 **현재 쓰는 visible mask 자체를 유지한 상태에서 outer silhouette만 추출하고 distance-transform 기반 edge distance를 계산하는 것**. 이 방식은 IoU/centroid와 같은 표현 공간을 유지하면서도 splat fringe와 contour sampling artifact를 줄일 수 있음.

---

## 4. 최종 권장 사항

### 우선 액션

**`_symmetric_contour_chamfer`를 대체할 설계 목표를 "현재의 GT/prior visible mask 위에서 outer silhouette만 사용하는 distance-transform 기반 edge metric"으로 고정하고, Gaussian-center hull 방향은 보류.**

### 근거

Sofa 77의 13.8px false-AMBIGUOUS 문제를 만드는 요인은 center geometry 자체보다도:
- 3x3 closing
- `mask & ~eroded` 경계 정의
- Internal seam 포함
- 1024개 subsampling
- Prior splat raster noise

즉 **현행 contour metric의 민감도** 쪽에 더 직접적으로 있음.

bbox IoU가 이미 0.81로 좋고 edge만 12.0 threshold를 조금 넘는 상황이면, 표현을 center-hull로 갈아엎기보다 **같은 mask 표현 안에서 edge distance를 더 robust하게 바꾸는 편이 훨씬 낮은 리스크**로 문제를 해결함. 이 방향은:
- IoU/centroid와의 일관성 유지
- 추가적인 opacity/hull/occlusion hyperparameter를 새로 들이지 않아도 됨

---

## 5. 참고 코드 위치

| 구성 요소 | 파일 | 라인 |
|----------|------|------|
| GT mask 생성 | `src/priorprobe/validation/prior_position_validator.py` | 462, 488-500 |
| GT semantic equality | 동일 | 495 |
| Binary closing | 동일 | 458-459 |
| Binary erosion | 동일 | 449-455 |
| Boundary point 추출 | 동일 | 798-808 |
| Symmetric contour chamfer | 동일 | 811-823 |
| Prior full render | 동일 | 681-692 |
| Prior isolated render | 동일 | 701-721 |
| Visible prior mask | 동일 | 724-742 |
| Fragmentation 처리 | 동일 | 874-878, 885, 909-913 |
| Habitat semantic source | `src/priorprobe/replica_export.py` | 838-841 |
| Point renderer fallback | 동일 | 882-905 |
| Canny edge (시각화) | `scripts/collect_prior_position_sweep.py` | 145, 158-161 |

---

what changed:
- Edge metric 측정 방식의 설계 리뷰를 Codex로 진행, 두 제안(GT edge 재탐색 / prior edge를 Gaussian center로) 각각의 장단점과 권장 액션을 정리.

what was checked:
- GT mask 생성 경로, binary closing/erosion kernel, boundary 추출 방식, prior mask visibility 로직, fragmentation 처리 경로의 현행 구현을 코드 라인 수준에서 확인.

what remains risky:
- Distance-transform 기반 edge metric으로 교체해도 `_boundary_points`의 1024 cap이나 fragment seam 처리 같은 부수 이슈는 별도 대응 필요.

next concrete action:
- `_symmetric_contour_chamfer`를 distance-transform 기반 outer-silhouette metric으로 교체. Gaussian center hull 방향은 보류.

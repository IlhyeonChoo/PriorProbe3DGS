# ScanNet Raw Root

원본 ScanNet 다운로드를 여기에 둔다. 이 경로는 보관용이며, 런타임이 직접 읽지 않는다.

권장 흐름:

1. 원본 ScanNet 장면을 이 경로에 둔다.
2. prior 비교에 사용할 subset scene만 골라낸다.
3. 각 subset을 `data/public_datasets/scannet_colmap/<scene_id>/`로 export한다.

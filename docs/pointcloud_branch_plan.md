# Pointcloud Branch Plan

Date: 2026-03-20

Branch: `exp/pointcloud`

Status: active baseline branch

## Role of This Branch

이 브랜치는 현재 PriorProbe3DGS의 기준선 실험 경로를 보존하는 장수 브랜치다.

- retrieval, alignment, backend wrapper, evaluation 흐름이 이미 연결된 baseline path를 유지한다.
- 기존 실험 결과와 비교 가능한 기준 구현을 제공한다.
- gaussian-direct 브랜치가 새로운 표현 계약을 실험하는 동안, 이 브랜치는 비교 축이 흔들리지 않도록 한다.

## Current Behavior of the Baseline

이 브랜치에서 prior source는 ShapeSplat gaussian asset일 수 있지만, 실제 insertion representation은 canonical RGB point cloud proxy다.

- retrieval 결과는 `gaussian_path`를 포함한다.
- alignment는 `canonical_seed_center/floor.ply`를 사용한다.
- multi-prior `merge` 계열 초기화는 point cloud 기준으로 동작한다.
- 현재 baseline의 의미는 "gaussian source를 pointcloud proxy로 정렬하고 삽입하는 prior-init"이다.

즉 이 브랜치는 "gaussian direct insertion" 구현이 아니라, 현재까지 검증되고 문서화된 pointcloud prior-init 경로를 담는다.

## Why This Branch Must Stay Separate

`exp/pointcloud`를 별도 브랜치로 유지하는 이유는 다음과 같다.

- 기존 결과와 설정을 기준선으로 보존하기 위해
- gaussian-direct 실험 때문에 baseline 의미가 바뀌는 것을 막기 위해
- retrieval / alignment / insertion의 표현 차이를 branch 단위로 분리하기 위해
- 실험 비교 시 코드 차이와 결과 차이를 명확히 대응시키기 위해

## What Changes Are Allowed Here

이 브랜치에서는 기준선 유지에 필요한 변경만 받는다.

- baseline 재현성을 높이는 버그 수정
- 공통 유틸 정리
- 평가, 문서, preset 정리
- 기존 pointcloud prior-init 의미를 바꾸지 않는 범위의 품질 개선

반대로 아래 변경은 이 브랜치의 기본 방향이 아니다.

- gaussian parameter direct insertion 실험
- pointcloud proxy를 버리는 구조 변경
- baseline과 실험 브랜치의 의미를 섞는 branch-specific hack

## How This Branch Differs From `exp/gaussian-direct`

두 브랜치의 차이는 구현 방식이 아니라 실험 가설 자체에 있다.

- `exp/pointcloud`는 pointcloud proxy prior-init을 기준선으로 유지한다.
- `exp/gaussian-direct`는 alignment와 insertion 표현을 분리하고, 원본 gaussian asset direct insertion을 실험한다.
- 둘은 직접 자주 merge하지 않고, 공통 가치가 있는 변경만 `main`을 통해 공유한다.

## Maintenance Policy

이 브랜치는 다음 원칙으로 관리한다.

### 1. Baseline Meaning Comes First

- 기존 실험 이름, 설정, 비교 축을 불필요하게 바꾸지 않는다.
- 코드 리팩터링이 있더라도 baseline behavior가 바뀌면 안 된다.

### 2. Common Code Moves Through `main`

- 공통 유틸이나 문서 정리는 `main`으로 정리한 뒤 다시 가져온다.
- gaussian-direct 전용 로직은 이 브랜치에 역으로 들여오지 않는다.

### 3. Outputs and Artifacts Stay Baseline-Oriented

- 이 브랜치의 산출물은 baseline 결과라는 의미를 유지해야 한다.
- lightweight metadata와 inspection 중심으로 기록하고, 대용량 생성물은 Git 밖에서 관리한다.
- branch 간 결과를 비교할 때는 동일 scene, 동일 iteration budget, 동일 preset naming을 유지한다.

### 4. Document Milestones

- 매 실험 시도마다 구조를 흔들지 않는다.
- 기준선 의미가 바뀌지 않는 milestone만 문서에 남긴다.

## Success Criteria for This Branch

이 브랜치는 다음 조건을 만족하면 잘 관리되고 있는 것이다.

- 기존 pointcloud prior-init baseline이 재현 가능하다.
- gaussian-direct 브랜치와 비교 가능한 기준 실험 preset이 유지된다.
- 공통 개선은 흡수하되, baseline semantics는 변하지 않는다.
- 브랜치 목적과 관리 원칙이 문서로 명시되어 있다.

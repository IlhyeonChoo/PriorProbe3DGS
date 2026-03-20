# Gaussian Direct Branch Plan

Date: 2026-03-20

Branch: `exp/gaussian-direct`

Status: pre-implementation planning note

## Environment and Output Policy

- 이 worktree는 `../PriorProbe3DGS`의 Python 3.11 환경을 기준으로 맞추되, 실행은 현재 worktree의 독립 `.venv`를 사용한다.
- generated prior manifest는 main worktree가 아니라 현재 worktree의 `outputs/gaussian_direct/prior_library/` 아래에 기록한다.
- backend run, evaluation, report, inspection 산출물은 모두 `outputs/gaussian_direct/` 아래로 모은다.
- `/mnt/...` 아래 staged asset과 dataset은 공유 자산으로 유지하되, worktree 로컬 산출물과 실험 이름은 pointcloud 기준선과 섞지 않는다.

## Current Project State

현재 프로젝트는 "prior를 쓴 vanilla 3DGS 초기화 경로를 실험하는 연구용 scaffold" 상태다.

- prior library, retrieval, alignment, backend wrapper, evaluation 흐름은 이미 연결되어 있다.
- ShapeSplat 계열 asset을 prior source로 사용하고, Replica/ScanNet 같은 scene-centric target dataset 위에서 prior-init 효과를 비교하는 구조다.
- 실험 preset과 결과 export 문서화는 어느 정도 정리되어 있다.
- pointcloud baseline과 prior-init baseline을 비교하는 현재 경로는 이미 여러 실험 결과와 문서가 누적되어 있다.

즉, 이 레포는 "아직 초기 단계"이긴 하지만, 완전히 빈 skeleton은 아니다. 이미 하나의 실험 경로가 사실상의 기준선으로 자리 잡고 있다.

## What We Expected vs. What The Current Code Actually Does

초기에 기대했던 것은 "retrieval로 선택한 ShapeSplat gaussian asset을 backend에 직접 넣는 prior-init"에 가까웠다. 하지만 현재 코드는 그와 다르게 동작한다.

- retrieval 결과는 `gaussian_path`를 유지하지만, 실제 alignment 입력은 `canonical_seed_center/floor.ply`다.
- `scripts/run_experiment.py`는 backend spec에 원본 gaussian asset이 아니라 `canonical_seed_path`를 `prior_ply`로 넘긴다.
- alignment search는 point cloud `xyz`와 bounding box를 기준으로 anisotropic scale을 계산한다.
- backend의 `replace` 경로는 gaussian을 직접 로드할 수 있지만, `merge` 계열은 결국 point cloud로 바꿔서 scene sparse cloud와 합친다.

정리하면 현재 "prior source"는 gaussian asset처럼 보이지만, 실제 "insertion representation"은 canonical RGB point cloud proxy다.

## Why This Is a Problem

이 상태는 pointcloud 기반 prior-init을 검증하는 데는 유효하지만, gaussian을 직접 삽입하는 실험을 하려면 몇 가지 문제가 생긴다.

- 원본 gaussian의 `opacity`, `scale_*`, `rot_*`, SH 계수가 multi-prior `merge`에서 보존되지 않는다.
- alignment와 insertion이 같은 표현을 쓴다는 전제가 코드 전체에 퍼져 있다.
- anisotropic scale은 point cloud proxy에는 자연스럽지만, gaussian asset에 그대로 적용하기에는 현재 backend 제약과 맞지 않는다.
- 기존 pointcloud 경로를 그대로 수정하면, 이미 쌓인 baseline 실험들과 비교 축이 흔들릴 수 있다.

즉 문제는 "단순 구현 미비"가 아니라, 현재 기준선 경로 자체가 pointcloud proxy 중심으로 굳어져 있다는 데 있다.

## Why This Branch Exists

`exp/gaussian-direct` 브랜치는 위 문제를 해결하기 위해 새로 분리했다.

브랜치를 나눈 이유는 명확하다.

- 기존 `exp/pointcloud` 브랜치를 현재 기준선으로 보존하기 위해
- gaussian-direct 실험이 기존 경로를 깨지 않도록 하기 위해
- 두 표현 방식의 차이를 코드, 설정, 산출물, 문서 단위에서 분명히 비교하기 위해
- 공통 유틸과 실험 전용 분기 로직을 분리해서 관리하기 위해

이 브랜치는 "현재 pointcloud 경로의 대체 구현"이 아니라, "새로운 prior insertion 가설을 검증하는 병렬 실험 경로"다.

## Planned Work In This Branch

이 브랜치에서 앞으로 진행할 작업은 아래 순서를 따른다.

### 1. Current Behavior Documentation

- 현재 pointcloud proxy 경로가 실제로 어떻게 동작하는지 명시적으로 문서화한다.
- gaussian-direct 경로의 목표와 현재 경로의 차이를 기록한다.
- branch-aware output / experiment naming 규칙을 정한다.

### 2. Handoff Split Between Alignment and Insertion

- alignment용 표현과 insertion용 표현을 분리한다.
- alignment는 기존 canonical seed point cloud를 계속 사용할 수 있다.
- insertion은 원본 gaussian asset을 source of truth로 유지한다.
- metadata에는 `source_prior_path`와 `canonical_seed_path`를 분리해서 남긴다.

### 3. Single-Prior Gaussian Replace Path

- 가장 먼저 single-prior `replace` 경로를 gaussian-direct 방식으로 검증한다.
- 이 단계의 목표는 "원본 gaussian asset이 backend로 실제 들어간다"를 보장하는 것이다.
- 이 단계에서 scale policy와 metadata policy를 먼저 고정한다.

### 4. Multi-Prior Gaussian Merge Path

- 기존 point cloud merge 대신 gaussian parameter 수준의 merge 경로를 검토한다.
- `merge`, `weighted_merge`, `filtered_merge`가 gaussian 단위에서 동작하도록 재설계한다.
- pointcloud reconversion 없이 prior 표현을 보존하는 경로를 구현한다.

### 5. Evaluation and Comparison

- 기존 `exp/pointcloud` 브랜치와 비교 가능한 preset을 만든다.
- 동일 scene, 동일 iteration budget, 동일 target category에서 비교한다.
- quality / speed / inspection 결과를 branch-aware 문서로 정리한다.

## How This Branch Must Differ From Existing Code

이 브랜치는 단순히 "기존 함수 몇 개 수정"으로 끝내지 않는 것이 원칙이다.

- 기존 pointcloud 경로는 기준선으로 남긴다.
- gaussian-direct 전용 runner, helper, config, experiment naming을 우선 고려한다.
- 기존 코드와 동일한 파일을 건드리더라도, pointcloud baseline의 동작 의미를 바꾸는 변경은 피한다.
- "공통 로직"과 "gaussian-direct 전용 로직"을 섞어서 확장하지 말고, 경계를 의식적으로 남긴다.

즉 이 브랜치의 핵심은 기능 추가 자체보다도 "표현 계약을 분리하는 새 경로"를 만드는 것이다.

## Maintenance Strategy To Avoid Conflicts

이 브랜치는 다음 원칙으로 관리한다.

### 1. Pointcloud Branch Is the Baseline, Not a Moving Target

- `exp/pointcloud`는 기존 실험 경로를 유지하는 기준선이다.
- gaussian-direct 실험을 위해 pointcloud 경로의 의미를 바꾸지 않는다.

### 2. Common Code Goes Upward, Experimental Code Stays Local

- 두 브랜치에서 공통으로 쓸 가치가 생긴 코드만 `main`으로 승격한다.
- 실험 전용 우회 로직, branch-specific hack, 미완성 API는 이 브랜치에 남긴다.
- 필요하면 `main`에서 공통 리팩터링 브랜치를 따서 정리한 뒤 다시 각 실험 브랜치로 가져간다.

### 3. Do Not Merge Experimental Branches Into Each Other Directly

- `exp/pointcloud`와 `exp/gaussian-direct`를 서로 직접 자주 merge하지 않는다.
- 공통 수정은 `main`으로 정리한 뒤 다시 배포한다.
- branch 간 비교 가능성을 깨는 history 혼합을 피한다.

### 4. Keep Outputs and Naming Branch-Aware

- experiment name prefix는 branch별로 분리한다.
- output root도 branch-aware하게 분리한다.
- lightweight metadata / inspection만 Git에 남기고, 대용량 생성물은 외부 storage 또는 ignored output으로 둔다.

### 5. Document Milestones, Not Every Trial

- 모든 시행착오를 코드 구조에 반영하지 않는다.
- milestone 단위로만 설계 문서와 실험 문서를 갱신한다.
- 실패한 방향도 버리기 전에 간단히 남겨서, 같은 실수를 반복하지 않게 한다.

## Initial Branch Success Criteria

이 브랜치의 첫 성공 기준은 다음과 같다.

- "gaussian을 직접 삽입하는 경로"가 pointcloud proxy 경로와 문서상, 코드상, 설정상으로 분리되어 있다.
- single-prior 기준으로 원본 gaussian asset direct insertion이 가능하다.
- 기존 pointcloud baseline과 비교 가능한 최소 1개 이상의 preset이 존재한다.
- branch-specific output / naming / documentation 규칙이 정리되어 있다.

## Final Note

이 브랜치는 기존 코드를 부정하기 위해 만든 것이 아니다. 현재 pointcloud 경로는 여전히 중요한 기준선이다. `exp/gaussian-direct`의 목적은 그 기준선을 유지한 채, "prior를 진짜 gaussian으로 넣으면 어떤 차이가 나는가"를 독립적으로 검증할 수 있는 실험 경로를 만드는 데 있다.

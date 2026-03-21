# 2단계 연구계획서

**프로젝트 총괄명:** ReCompose3D  
**작성일:** 2026-03-16  
**작성자:** 추일현

---

## 문서 개요

본 문서는 사전 학습된 3D Gaussian Splatting(3DGS) object prior를 재사용하여 장면 최적화 시간을 단축하는 연구를 2단계로 분리하여 기술한다.

| 단계 | 레포지토리 | 핵심 질문 |
|------|-----------|----------|
| 1단계 | **PriorProbe3DGS** | 도메인 보강 prior가 실제로 최적화 시간을 줄이는가? |
| 2단계 | **ReCompose3D** | 검증된 prior 전략이 기존 가속축과 결합되었을 때 시스템 수준의 효율성을 달성하는가? |

1단계는 prior 자체의 기여를 식별하는 데 집중하고, 2단계는 결합형 시스템의 성능을 검증하는 데 집중한다. 두 연구는 별도 레포지토리로 관리하며, 2단계는 1단계 결과를 dependency로 참조한다.

---

# 1단계: PriorProbe3DGS

## 1. 연구명

**도메인 증분 prior를 활용한 반복 객체 장면에서의 3D Gaussian Splatting 최적화 시간 단축 검증**

## 2. 연구 배경 및 필요성

3D Gaussian Splatting(3DGS)은 sparse point 기반 초기화와 iterative optimization을 통해 고품질 장면 재구성을 수행하지만, 장면별 최적화 비용이 여전히 크고 초기화 품질에 따라 수렴 특성이 크게 달라진다. ShapeSplat은 object-level 3DGS prior와 representation learning의 가능성을 보여주었고, GaussianObject는 적은 입력 이미지로도 object-level Gaussian reconstruction이 가능함을 보였다.

따라서 대규모 prior를 처음부터 새로 학습하기보다는, 기존 prior 라이브러리에 소량의 도메인 객체를 증분 추가해 재사용하는 전략은 현실적이며 연구 가치가 높다.

본 단계의 목적은 복잡한 전체 파이프라인을 한 번에 주장하는 것이 아니라, **"도메인 보강된 prior가 실제로 시간을 줄이는가"**를 깨끗한 조건에서 먼저 검증하는 것이다.

## 3. 연구 목적

- 도메인 보강 prior가 from-scratch 3DGS 대비 전체 optimization time과 time-to-target quality를 감소시키는지 검증한다.
- occlusion 강도에 따라 prior 재사용의 효과가 어떻게 달라지는지 분석한다.
- ShapeSplat 그대로 사용, 객체 증분 추가, 경량 추가학습 중 어느 전략이 가장 실용적인지 판단한다.
- 성능 저하가 발생할 경우, oracle 비교군을 통해 prior 품질, retrieval 품질, insertion 품질 중 어디서 병목이 발생하는지 분리한다.

## 4. 핵심 가설

1. 도메인 증분 prior를 사용하면 from-scratch 3DGS 대비 total optimization time과 time-to-target quality가 감소한다.
2. occlusion이 약한 장면에서는 prior 재사용의 이득이 크고 안정적이지만, occlusion이 강한 장면에서는 retrieval 오류와 정렬 오류 때문에 이득이 감소한다.
3. prior 효과를 정확히 평가하려면 prior 품질, retrieval 품질, insertion 품질을 분리해서 측정해야 한다.

## 5. 연구 범위

- **배경:** 빈 방 또는 배경 텍스처가 단순한 실내 공간
- **객체 수:** 1~3개 수준의 소수 객체
- **장면 조건:** 약한 occlusion과 강한 occlusion 분리
- **prior 구성:**
  - ShapeSplat 기본 prior
  - ShapeSplat + 도메인 객체 증분 추가
  - 증분 추가 후 경량 추가학습 또는 적응
- **비교군:** from-scratch 3DGS, prior reuse, oracle prior, oracle alignment (총 6개, 아래 상세)

## 6. 연구 방법

### 6.1 데이터 전략

데이터 수집은 두 단계로 진행한다.

**Phase A — 공개 데이터셋 활용.** Replica, ScanNet 등 배경이 단순한 실내 장면 데이터셋을 기본으로 사용한다. 이 단계에서 prior 라이브러리에 도메인 관련 객체의 특징(feature)을 추가하고, 각 객체의 실제 크기(metric scale) 정보를 보조 메타데이터로 함께 기록한다.

**Phase B — 직접 촬영 데이터 추가.** Phase A에서 검증된 파이프라인을 바탕으로, 직접 촬영한 실내 장면 데이터를 추가하여 도메인 일치도가 높은 조건에서의 성능을 확인한다.

### 6.2 객체 크기 정보의 역할

각 prior 객체에 실제 크기(metric scale) 정보를 보조 메타데이터로 부여한다. 이 정보는 1단계 연구의 핵심 novelty가 아니라 insertion 정확도를 보조하는 역할로 취급한다. 구체적으로, 크기 정보는 삽입 시 물체가 벽이나 바닥에 매몰되거나 다른 객체와 부자연스럽게 겹치는 문제를 방지하는 데 활용된다. 본격적인 활용은 후속 연구에서 다룬다.

### 6.3 prior 라이브러리 구성

기존 ShapeSplat prior를 기본값으로 사용한다. 이후 도메인과 직접 관련된 객체를 소량 수집하여 3DGS 형태로 증분 추가한다. 증분 추가란 기존 라이브러리의 index에 새로운 객체 항목과 대응 feature를 추가하는 것을 의미하며, 성능 향상이 충분하지 않을 경우에만 retrieval encoder 또는 prior embedding에 대한 경량 추가학습을 수행한다.

### 6.4 controlled scene 설계

장면은 가능한 한 단순한 실내 공간으로 제한한다. 배경 복잡도를 낮춰 prior 재사용 효과를 명확히 관찰할 수 있도록 하고, 객체 간 배치만 조절하여 occlusion 수준을 통제한다. occlusion 수준은 projected mask overlap 또는 visible area ratio와 같은 정량 지표로 정의한다.

### 6.5 비교군 설계 및 실행 순서

비교군은 총 6개이며, 원인 분리를 위해 전부 필요하다. 실행 순서는 다음과 같다.

**1순위 (핵심 검증):**

| 비교군 | 목적 |
|--------|------|
| from-scratch 3DGS | baseline |
| oracle prior | prior 재사용이 원리적으로 효과가 있는가 확인. 여기서 시간 절감이 없으면 접근 자체를 재고 |

**2순위 (상한선 확인):**

| 비교군 | 목적 |
|--------|------|
| oracle prior + oracle alignment | retrieval과 alignment이 완벽할 때의 성능 상한선 |

**3순위 (자동화 gap 측정):**

| 비교군 | 목적 |
|--------|------|
| ShapeSplat 기본 prior + 자동 alignment | oracle 대비 gap이 retrieval 문제인지 alignment 문제인지 분리 |

**4순위 (도메인 보강 효과):**

| 비교군 | 목적 |
|--------|------|
| 도메인 증분 prior + 자동 alignment | 증분 추가로 gap이 얼마나 회복되는지 |
| 도메인 증분 prior + 경량 적응 | 추가학습이 필요한지, 어느 정도면 충분한지 |

이 순서를 따르면, 중간에 결과가 나쁘더라도 어느 단계에서 병목이 생기는지 단계적으로 진단할 수 있다.

### Oracle Prior 3단계 세분화

Oracle prior 실험은 아래 3개 조건으로 단계적으로 설계한다.

| 조건 | 설명 | 측정 목적 |
|------|------|-----------|
| **A: Oracle Prior + Oracle Alignment** | 데이터셋에서 객체를 별도 학습 → 해당 객체가 있던 위치에 GT pose로 삽입 | prior 재사용의 **이론적 상한선** (ceiling) |
| **B: 동일 객체 lib 보유 + 자동 retrieval/insertion** | 동일 객체가 lib에 존재하는 상태에서 자동 파이프라인으로 탐색·삽입 | 자동화 파이프라인의 **이상적 조건 성능** |
| **C: 동일 객체 lib 미보유 (해당 객체만 제거)** | lib에서 target 객체를 제거하고 유사 객체로 매칭 | **현실적 시나리오** 성능 |

진단 흐름: A → B 비교는 자동화 파이프라인의 gap을, B → C 비교는 retrieval의 실제 robustness를 측정한다.

조건 A는 데이터셋 내 객체를 독립 학습하여 oracle prior를 생성하므로 information leakage 가능성이 있다. 이 조건은 **이론적 상한선 참조용**이므로 실험의 주요 결론에 영향을 주지 않는다. 실험 설계 문서에 disclaimer로 명시한다.

### 6.6 insertion의 취급

1단계에서 insertion은 독립 연구 주제가 아니라 통제변수 또는 보조 모듈로 둔다. insertion은 가능한 한 고정된 방법으로 처리하고, oracle alignment를 통해 상한선을 함께 측정한다. optimizer, learning rate schedule, densification policy 역시 모든 비교군에서 동일하게 유지하여 prior 효과만 먼저 식별한다.

### 6.7 Retrieval 전략

Retrieval은 **2단계 매칭 구조**를 채택한다.

| 단계 | 방법 | 설명 |
|------|------|------|
| 1단계 (Coarse) | OpenCLIP (ViT-B/32 또는 ViT-L/14) | image embedding 기반 cosine similarity로 카테고리 분류 |
| 2단계 (Fine) | ShapeSplat pretrained feature | feature space에서 nearest neighbor로 형상 유사도 기반 최종 매칭 |

1단계를 과도하게 정교하게 만들면 "간단한 retrieval로도 prior reuse가 효과적이다"라는 더 강한 메시지를 놓친다. 1단계 coarse retrieval의 단순성은 의도적인 설계 선택이다.

mean_rgb 방식은 조명 변화에 취약하고 형상 정보가 없어 주력으로는 부적합하며, 보조 baseline으로만 활용 가능하다.

## 7. 실험 설계 요약

| 항목 | 설정 |
|------|------|
| 장면 종류 | 빈 방 또는 배경이 단순한 실내 controlled scene |
| 객체 수 | 1~3개 |
| occlusion | 약한 경우 / 강한 경우 분리 |
| prior 변형 | 기본 prior / 증분 추가 / 경량 적응 |
| 비교군 | from-scratch / prior reuse / oracle prior / oracle alignment (총 6개) |
| 통제 변수 | optimizer, densification, 학습 스케줄, 렌더링 설정 |
| 데이터 | Phase A: 공개 데이터셋, Phase B: 직접 촬영 |

## 8. 평가 지표

**핵심 지표:**
- total optimization time
- time-to-target quality — 아래 4개 지표로 측정

| # | 지표 | 설명 |
|---|------|------|
| 1 | **상대 품질 threshold 도달 시간** | vanilla 수렴 품질의 80%, 90%, 95% 각각에 도달하는 wall-clock time 비교 |
| 2 | **최종 수렴 품질 도달 가능 여부** | prior 삽입이 local minimum에 빠뜨려서 최종 품질 자체가 떨어지는지 확인 |
| 3 | **30K iter 고정 시 품질** | 고정 iteration budget에서의 PSNR/SSIM/LPIPS 비교 |
| 4 | **동일 wall-clock time 고정 시 품질** (보조) | prior 삽입으로 per-iteration 비용이 변할 수 있으므로, 동일 시간 기준 비교 추가 |

threshold는 절대값 대신 상대값을 사용한다. 장면마다 달성 가능한 최대 품질이 다르기 때문이다. 지표 3과 4를 분리하는 이유는 Gaussian 수가 초기부터 많으면 렌더링/backward 비용이 증가하여 iter 기준과 시간 기준 결과가 다를 수 있기 때문이다.

**보조 지표:**
- convergence iteration 수
- 최종 PSNR / SSIM / LPIPS
- retrieval top-1 / top-k 정확도
- alignment success rate 또는 mask IoU
- 최종 Gaussian 수 및 densification 증가량

## 9. 기대 효과

- prior 재사용 자체의 실효성을 독립적으로 검증할 수 있다.
- 어떤 수준의 도메인 보강이 필요한지 실증적으로 제시할 수 있다.
- occlusion이 prior 재사용 성능에 미치는 영향을 구조적으로 설명할 수 있다.
- 결과가 부정적이더라도 oracle 비교군을 통해 어디서 병목이 발생하는지 진단할 수 있다.
- 이후 2단계 연구에서 사용할 prior 전략을 근거 있게 선택할 수 있다.

## 10. 위험요인 및 대응

| 위험요인 | 대응 |
|----------|------|
| retrieval mismatch | oracle prior 실험을 별도 수행해 영향 분리 |
| pose misalignment | oracle alignment와 자동 alignment를 분리 평가 |
| 추가학습 비용 과다 | full retraining 대신 증분 추가와 경량 적응에 우선순위 부여 |
| 장면이 너무 단순해 일반성이 약함 | 2단계에서 clutter와 복잡도를 확장해 보완 |
| oracle에서도 효과가 없음 | 접근 자체를 재고하고 실패 분석 논문으로 전환 |

## 11. 예상 일정

| 기간 | 주요 작업 |
|------|----------|
| 1개월차 | prior 라이브러리 구성, 도메인 객체 수집, 크기 메타데이터 정리 |
| 2개월차 | controlled scene 구축(공개 데이터셋 기반), occlusion 수준 정의 |
| 3개월차 | 1순위 실험: from-scratch vs oracle prior |
| 4개월차 | 2~3순위 실험: oracle alignment, 자동 retrieval/alignment |
| 5개월차 | 4순위 실험: 증분 추가 및 경량 적응, Phase B 데이터 추가 |
| 6개월차 | 결과 정리, 실패 사례 분석, ablation |
| 7개월차 | 논문 초안 작성 및 도표 정리 |

---

# 2단계: ReCompose3D

## 1. 연구명

**사전 학습 object prior와 가속 최적화를 결합한 효율적 3D Gaussian Splatting 파이프라인 연구**

## 2. 연구 배경 및 필요성

1단계(PriorProbe3DGS)가 prior 재사용의 유효성을 통제된 환경에서 검증하는 연구라면, 2단계는 그 결과를 기존의 3DGS 가속축과 결합해 시스템 수준의 time-quality trade-off를 입증하는 연구다.

3DGS-LM은 optimizer replacement를 통해 최적화 시간을 줄였고, InstantSplat은 sparse-view 및 pose-free 초기화 방향을 제시했으며, RAIN-GS는 초기화가 불완전할 때의 강건성을 높였다. prior reuse는 이들과 경쟁하는 축이라기보다, 결합 가능한 축으로 보는 것이 적절하다.

본 단계의 목적은 "prior reuse만으로 빨라졌다"를 넘어서, prior reuse와 기존 가속축이 실제 파이프라인에서 어떻게 결합되는지를 실험적으로 보여주는 데 있다.

## 3. 연구 목적

- 1단계에서 검증된 prior 전략을 기반으로 전체 파이프라인 수준의 효율성을 입증한다.
- 동일 품질 달성에 필요한 시간 감소율과, 동일 시간 예산에서의 품질 향상 폭을 동시에 분석한다.
- prior reuse가 기존 가속축과 상보적인지, 중복되는지, 또는 특정 조건에서만 유효한지를 설명한다.

## 4. 핵심 가설

1. prior reuse와 LM 기반 optimizer replacement는 서로 다른 병목을 줄이므로 결합 시 더 큰 시간 절감 효과를 낸다.
2. prior reuse와 sparse-view 초기화는 입력 view 수가 적을수록 결합 효과가 커진다.
3. 복잡한 실내 장면에서도 적절한 prior reuse 전략은 baseline 대비 더 좋은 time-quality Pareto frontier를 형성한다.

## 5. 연구 범위

- 1단계에서 가장 안정적이었던 prior 전략만 채택하여 고정
- 장면 복잡도 확장: clutter가 존재하는 repeated-object 실내 장면
- 1단계 결과에 따라 가장 유망한 1~2개 결합축을 우선 선택하고, 나머지는 보조 실험으로 배치

## 6. 연구 방법

### 6.1 prior 전략 고정

2단계에서는 prior 설계 자체를 다시 흔들지 않는다. 1단계에서 검증된 prior 모듈을 고정한 상태에서, 다른 가속축과의 결합 효과만 분석한다.

### 6.2 비교군 설계

주요 실험은 조합형 비교로 구성하되, 1단계 결과에 따라 scope를 조정한다.

**핵심 비교군:**
- baseline 3DGS
- prior only (1단계 최적 전략)
- LM only (3DGS-LM)
- prior + LM

**확장 비교군 (1단계 결과에 따라 선택):**
- sparse-view initialization only
- prior + sparse-view initialization
- prior + LM + sparse-view initialization

이를 통해 additive effect, complementary effect, redundancy를 구분한다.

### 6.3 데이터 및 장면 확장

1단계 controlled scene 외에 반복 객체가 다수 존재하고 배경 clutter가 포함된 실제 실내 장면을 사용한다. 객체 수, occlusion 수준, view 수, 도메인 일치도를 점진적으로 증가시켜 파이프라인 일반성을 평가한다.

### 6.4 Pareto 분석 중심의 평가

2단계의 핵심은 단순한 속도 비교가 아니라 Pareto 분석이다. 동일 품질 기준 시간 감소율과 동일 시간 기준 품질 향상을 함께 제시한다. 결과는 time-to-quality curve, quality-vs-time Pareto frontier, failure rate, scaling behavior를 중심으로 해석한다.

### 6.5 보조 ablation의 위치

object/background learning rate 차등화, densification policy 조정 등은 본 단계의 주 novelty가 아니라 보조 ablation으로 둔다. 주 메시지는 prior reuse의 결합 가능성과 시스템 수준 효율성에 집중한다.

## 7. 실험 설계 요약

| 항목 | 설정 |
|------|------|
| prior 전략 | 1단계에서 검증된 최적 prior 고정 |
| 가속축 | LM 기반 optimizer, sparse-view 초기화 (1단계 결과에 따라 선택) |
| 데이터 | clutter가 있는 repeated-object 실내 장면 |
| 비교군 | baseline / prior / LM / 결합형 조합 |
| 주요 분석 | 동일 품질 기준 시간 감소율, 동일 시간 기준 품질 향상, Pareto frontier |
| 보조 분석 | failure rate, scaling behavior, view 수 변화 민감도 |

## 8. 평가 지표

**핵심 지표:**
- 동일 품질 기준 total time 감소율
- 동일 시간 기준 PSNR / SSIM / LPIPS
- Pareto frontier 비교

**보조 지표:**
- convergence iteration 수
- failure rate
- 장면 규모 증가에 따른 scaling behavior
- sparse-view 조건에서의 성능 변화
- occlusion 및 clutter 증가에 따른 robustness

## 9. 기대 효과

- prior reuse가 3DGS acceleration ecosystem 안에서 어떤 위치를 가지는지 설명할 수 있다.
- optimizer acceleration, initialization acceleration과의 상보성을 정량적으로 제시할 수 있다.
- 실사용 관점에서 어떤 조합이 가장 효율적인지 설계 원칙을 제공할 수 있다.

## 10. 위험요인 및 대응

| 위험요인 | 대응 |
|----------|------|
| novelty dilution | 가속축을 한 번에 넣지 않고, primary comparison과 secondary ablation 분리 |
| 비교군 폭증 | 1단계 결과에 따라 유망한 1~2개 결합축을 우선 선택 |
| 결합 효과가 작을 가능성 | 어떤 조합이 중복이고 어떤 조합이 상보적인지 구조적 해석 |
| 1단계 결과 의존성 | 1단계에서 가장 안정적인 prior 전략을 확보한 뒤에만 2단계 착수 |

## 11. 예상 일정

| 기간 | 주요 작업 |
|------|----------|
| 1개월차 | 1단계 최적 prior 고정, 결합 대상 가속 기법 선정 |
| 2개월차 | baseline / prior only / LM only 구축 |
| 3개월차 | 결합형 조합 구현 및 기본 실험 |
| 4개월차 | 복잡한 장면 및 sparse-view 조건 비교 실험 |
| 5개월차 | Pareto 분석, failure case 정리, 보조 ablation |
| 6개월차 | 논문 초안 작성 및 결과 정리 |

---

# 단계 간 관계

## 착수 조건

- **2단계 착수 조건:** 1단계에서 oracle prior 조건이 from-scratch 대비 유의미한 시간 절감을 보이고, prior mismatch와 insertion failure를 일정 수준 이하로 통제할 수 있을 것
- **1단계 완료 기준:** prior reuse가 controlled scene에서 time-to-target quality와 total optimization time을 안정적으로 개선하는지 확인

## 핵심 설계 원칙

1. 1단계는 prior 효과 식별에 집중한다.
2. 2단계는 prior를 고정하고 결합형 파이프라인 효율성을 검증한다.
3. 1단계와 2단계의 novelty를 명확히 분리한다.
4. 두 단계는 별도 레포지토리로 관리하며, 2단계는 1단계 코드를 dependency로 참조한다.

---

# 참고 문헌(대표)

1. Kerbl, B., Kopanas, G., Leimkühler, T., & Drettakis, G. **3D Gaussian Splatting for Real-Time Radiance Field Rendering**. ACM TOG, 2023.
2. Qi, M. et al. **ShapeSplat: A Large-scale Dataset of Gaussian Splats and Their Self-Supervised Pretraining**. 2024.
3. Höllein, L., Božič, A., Zollhöfer, M., & Nießner, M. **3DGS-LM: Faster Gaussian-Splatting Optimization with Levenberg-Marquardt**. ICCV, 2025.
4. Fan, Z. et al. **InstantSplat: Sparse-view Gaussian Splatting in Seconds**. 2024.
5. Jung, J. et al. **Relaxing Accurate Initialization Constraint for 3D Gaussian Splatting**. 2024.
6. Yang, C. et al. **GaussianObject: High-Quality 3D Object Reconstruction from Four Views with Gaussian Splatting**. ACM TOG, 2024.

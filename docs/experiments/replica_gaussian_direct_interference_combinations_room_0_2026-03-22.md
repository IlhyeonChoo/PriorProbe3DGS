# Replica Gaussian-Direct Interference Combinations

- Date: 2026-03-22
- Scene: `room_0`
- Dataset family: `roomwide_v2_384`
- 비교 기준: baseline / prior 100K none / A prior_25k / 진단 실험 핵심(B, C)
- 주 지표: `iter_0`, `iter_3000`, `iter_15000` PSNR/SSIM/LPIPS와 gaussian count
- 참고: `time_to_target_sec`는 표에는 남기되 판단의 주 근거로 쓰지 않음

## Summary

| label | group | protection | sh_reset | prior_budget | sfm_replace | sfm_removed | iter_0_psnr | iter_3000_psnr | iter_15000_psnr | gaussians@0 | gaussians@3000 | gaussians@15000 |
|---|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | reference | none | None | None | None | n/a | 8.142288662493229 | 10.32485580444336 | 12.233680725097656 | 100000 | 1098647 | 4569461 |
| prior 100K none | reference | none | None | None | None | n/a | 8.011765368282795 | 10.486681938171387 | 12.270485877990723 | 200000 | 1218554 | 4568764 |
| A prior_25k | reference | none | none | 25000 | none | 0 | 8.099511548876762 | 10.56064224243164 | 12.289521217346191 | 125000 | 1183260 | 4667135 |
| B replace_region | diagnostic | none | none | 0 | aligned_prior_aabb_union | 16420 | 8.170989327132702 | 10.561450004577637 | 12.253632545471191 | 183580 | 1195419 | 4601648 |
| C sh_zero | diagnostic | none | zero_all | 0 | none | 0 | 8.13888767361641 | 10.441508293151855 | 12.260777473449707 | 200000 | 1197645 | 4692917 |
| A+C | combination | none | zero_all | 25000 | none | 0 | 8.150294288992882 | 10.565749168395996 | 12.279438018798828 | 125000 | 1154103 | 4593861 |
| A+C weak(0.02) | combination | weak(0.02) | zero_all | 25000 | none | 0 | 8.15037715435028 | 10.436753273010254 | 12.266573905944824 | 125000 | 1095030 | 4463525 |
| A+B | combination | none | none | 25000 | aligned_prior_aabb_union | 16402 | 8.136560037732124 | 10.483664512634277 | 12.233482360839844 | 108598 | 1152439 | 4635505 |
| A+B+C | combination | none | zero_all | 25000 | aligned_prior_aabb_union | 16397 | 8.081108540296555 | 10.477097511291504 | 12.28952407836914 | 108603 | 1114550 | 4636244 |

## Combination Focus

| label | iter_0 vs A25K | iter_3000 vs A25K | final vs A25K | iter_0 vs baseline | final vs baseline | prior_kept_total | sfm_removed_ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| A+C | +0.050783 | +0.005107 | -0.010083 | +0.008006 | +0.045757 | 25000 | 0.000000 |
| A+C weak(0.02) | +0.050866 | -0.123889 | -0.022947 | +0.008088 | +0.032893 | 25000 | 0.000000 |
| A+B | +0.037048 | -0.076978 | -0.056039 | -0.005729 | -0.000198 | 25000 | 0.164020 |
| A+B+C | -0.018403 | -0.083545 | +0.000003 | -0.061180 | +0.055843 | 25000 | 0.163970 |

## Insertion Diagnostics

| label | prior_original_total | prior_kept_total | protected@3000 | protected@15000 | sfm_removed_ratio | total_time_sec | time_to_target_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 0 | 0 | n/a | n/a | n/a | 692.3747557080351 | 138.474951 |
| prior 100K none | 100000 | 100000 | 94809 | 64287 | n/a | 714.8504251777194 | 142.970085 |
| A prior_25k | 100000 | 25000 | 24396 | 18143 | 0.000000 | 712.6845968835987 | 142.536919 |
| B replace_region | 100000 | 100000 | 93937 | 64009 | 0.164200 | 1332.0661474862136 | 266.413229 |
| C sh_zero | 100000 | 100000 | 84576 | 49524 | 0.000000 | 1313.3537895157933 | 262.670758 |
| A+C | 100000 | 25000 | 22951 | 13404 | 0.000000 | 704.193411081098 | 140.838682 |
| A+C weak(0.02) | 100000 | 25000 | 25000 | 25000 | 0.000000 | 714.5421231607907 | 142.908425 |
| A+B | 100000 | 25000 | 24610 | 18065 | 0.164020 | 705.6192728080787 | 141.123855 |
| A+B+C | 100000 | 25000 | 20939 | 14247 | 0.163970 | 703.5484078750014 | 140.709682 |

## Interpretation Hints

- 현재 기준 비교점 `A prior_25k`: iter_0 `8.099511548876762`, iter_3000 `10.56064224243164`, final `12.289521217346191`
- `A+B` final delta vs A25K: `-0.056039` dB
- `A+C` final delta vs A25K: `-0.010083` dB
- `A+B+C` final delta vs A25K: `+0.000003` dB
- `A+C weak` vs `A+C` at iter_3000: `-0.128996` dB
- `A+C weak` vs `A+C` final: `-0.012864` dB

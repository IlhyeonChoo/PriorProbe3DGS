---
license: cc-by-nc-4.0
language:
- en
pretty_name: ModelNet_Splats
size_categories:
- 10B<n<100B
extra_gated_prompt: |
  If you find our method/dataset helpful, please consider citing our paper:
  
  @inproceedings{ma2025large,
    title={A Large-Scale Dataset of Gaussian Splats and Their Self-Supervised Pretraining},
    author={Ma, Qi and Li, Yue and Ren, Bin and Sebe, Nicu and Konukoglu, Ender and Gevers, Theo and Van Gool, Luc and Paudel, Danda Pani},
    booktitle={2025 International Conference on 3DV},
    pages={145--155},
    year={2025},
    organization={IEEE}
  }
---

This repository contains ShapeSplat, a large dataset of Gaussian splats spanning 65K objects in 87 unique categories (gathered from ShapeNetCore, ShapeNet-Part, and ModelNet).

ModelNet_Splats consists of the 12 objects across 40 categories of ModelNet40.

The data is distributed as ply files where information about each Gaussian is encoded in custom vertex attributes.
Please see [DATA.md](DATA.md) for details about the data.

If you use the ModelNet_Splats data, you agree to abide by the [ModelNet terms of use](https://modelnet.cs.princeton.edu/#). You are only allowed to redistribute the data to your research associates and colleagues provided that they first agree to be bound by these terms and conditions.

If you find the data helpful, please consider citing the ShapeSplat paper.
```
@article{ma2024shapesplat,
  title={ShapeSplat: A Large-scale Dataset of Gaussian Splats and Their Self-Supervised Pretraining},
  author={Ma, Qi and Li, Yue and Ren, Bin and Sebe, Nicu and Konukoglu, Ender and Gevers, Theo and Van Gool, Luc and Paudel, Danda Pani},
  journal={arXiv preprint arXiv:2408.10906},
  year={2024}
}

@article{chang2015shapenet,
  title={Shapenet: An information-rich 3d model repository},
  author={Chang, Angel X and Funkhouser, Thomas and Guibas, Leonidas and Hanrahan, Pat and Huang, Qixing and Li, Zimo and Savarese, Silvio and Savva, Manolis and Song, Shuran and Su, Hao and others},
  journal={arXiv preprint arXiv:1512.03012},
  year={2015}
}
```
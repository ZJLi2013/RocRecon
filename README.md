# RocRecon

> 中文 | [English](README-en.md)

**RocRobSim 平台的 real2sim 资产侧——当前是一条 object-level 的 gen3d 管线。**

把一段 prompt 或一张参考图，生成单物体的**可直接进仿真的资产目录**——缩放好、物理合理的
mesh，加上带碰撞体的 URDF，开箱即可放进机器人仿真器。


它是纯粹的**生产端**：只产出文件，**不依赖任何下游消费者**（资产库、SDG 数据引擎等）。
消费者通过自己的 catalog / metadata 步骤来摄入产物目录。

## RocRecon 的定位

```
rocm3d          （ROCm 使能：让开源 3D 生成模型跑在 AMD GPU 上）
   │  使能
   ▼
RocRecon        （real2sim 管线：prompt/图像 -> 可仿真 URDF 资产）   <-- 本仓库
   │  产出资产目录
   ▼
RoboSmith       （SDG 数据引擎：消费 资产 + 任务 -> 训练数据）
```

- **rocm3d** 是把生成模型移植到 ROCm 的兼容性 skill 集。RocRecon **使用** ROCm-ready 的模型，
  本身不做移植。
- **RoboSmith** 消费 RocRecon 的产物，但自己不做资产生成。


## 安装

```bash
pip install -e .            # 核心（trimesh + numpy）
pip install -e ".[gen]"     # + torch / pillow，用于运行生成后端
```

生成后端还需要本机上对应的模型仓库（如 TRELLIS.2、Hunyuan3D、TripoSG）。
ROCm 环境与模型部署见 [docs/rocm-setup.md](docs/rocm-setup.md)，各后端的安装提示可查询：

```python
import rocrecon
for info in rocrecon.list_backend_info():
    print(info.name, info.install_hint)
```

## 用法

```python
import rocrecon

# 从一张图产出可仿真资产目录（TRELLIS.2 需要 image_path）
out = rocrecon.generate_asset(
    "red ceramic mug",
    output_dir="assets/red_mug",
    backend="trellis2",
    image_path="mug.png",
    target_size_m=0.1,
)
# out/ 目录现在包含：model.urdf、visual.glb（或 .obj）、collision.obj、
#                   reference.png、generation.json
```

不跑生成后端，直接把已有 mesh 转成资产：

```python
import trimesh
from rocrecon import mesh_to_urdf

mesh = trimesh.load("chair.glb", force="mesh")
mesh_to_urdf(mesh, "assets/chair", name="chair", target_size_m=0.8, mass_kg=3.0)
```

## 产物契约

一个产出的资产目录包含：

| 文件 | 作用 |
| --- | --- |
| `model.urdf` | 可仿真 URDF（visual + collision 两类 link） |
| `visual.glb` / `visual.obj` | 视觉 mesh（有纹理时为 GLB） |
| `collision.obj` | 凸包 / 简化后的碰撞 mesh |
| `reference.png` | 输入参考图（如有提供） |
| `generation.json` | 溯源清单（prompt、backend、model、耗时） |

消费者在此之上叠加自己的 `metadata.json` / catalog 记录。
canonical frame 契约与 prompt 指南见 [docs/asset-generation.md](docs/asset-generation.md)。

## 生成后端

| 后端 | 模型 | ROCm 状态 |
| --- | --- | --- |
| `trellis2` | Microsoft TRELLIS.2-4B（图生 3D，PBR） | 已验证（MI300X） |
| `hunyuan3d` | Tencent Hunyuan3D | 社区 fork |
| `triposg` | TripoSG | 待验证 |


## Next Step

当前只做 object-level 生成（prompt / 单图 → 单物体 sim-ready URDF），尚无真正的 3D 重建：

- [ ] 单物体真实重建（real RGB-D / 视频 / 扫描 → asset）
- [ ] 场景级 real2sim 重建（多物体布局、场景结构）


## 文档

- [docs/asset-generation.md](docs/asset-generation.md) — canonical frame 契约、prompt 指南、产物契约
- [docs/rocm-setup.md](docs/rocm-setup.md) — TRELLIS.2 / 生成后端的 ROCm 部署
- [docs/extending-backends.md](docs/extending-backends.md) — 开发者：新增后端（含从 rocm3d 引入模型）、扩展性与最终目标

## 参考

- TRELLIS.2 — [microsoft/TRELLIS](https://github.com/microsoft/TRELLIS)（ROCm fork [ZJLi2013/TRELLIS.2](https://github.com/ZJLi2013/TRELLIS.2)）
- Hunyuan3D-2 — [Tencent-Hunyuan/Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)
- Articraft — [mattzh72/articraft](https://github.com/mattzh72/articraft)
- Objaverse — [allenai/objaverse-xl](https://github.com/allenai/objaverse-xl)

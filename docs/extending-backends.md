# 开发者：新增后端（含从 rocm3d 引入模型）

RocRecon 的可扩展点是**后端**：后端只负责「产出一个 mesh」，其余（缩放、质量、碰撞体、URDF、
manifest）由 `produce.py` 统一完成。所以接一个新模型 = 写一个后端类，下游零感知。

## 1. 后端契约

后端实现 `rocrecon.backend.GenBackend`：

```python
import trimesh
from rocrecon.backend import GenBackend, BackendInfo, register_backend


@register_backend("mymodel")          # 注册名，get_backend("mymodel") 即可拿到
class MyBackend(GenBackend):
    def __init__(self, device="auto", repo_path=None, **kw):
        self._repo_path = repo_path   # 在哪找模型 repo（见 §2）
        self._pipeline = None

    @property
    def info(self) -> BackendInfo:
        return BackendInfo(
            name="mymodel",
            model_name="MyModel-XB (image-to-3D)",
            has_pbr=False,
            min_vram_gb=16.0,
            rocm_status="verified",   # verified / community_fork / likely / unknown
            install_hint="git clone ... && pip install ...",
        )

    def is_available(self) -> bool:
        # 轻量探测：repo 在不在、torch 在不在
        ...

    def generate(self, prompt, output_path=None, **kwargs) -> trimesh.Trimesh:
        self._ensure_pipeline()       # lazy 加载（见 §3）
        mesh = ...                    # 跑模型 -> trimesh.Trimesh
        if output_path is not None:
            mesh.export(str(output_path))
        return mesh
```

把文件放到 `rocrecon/mymodel_backend.py`，并加进 `backend.py` 的 `_discover_builtins()` 列表，
import `rocrecon` 时即自注册。

## 2. 从 rocm3d 引入一个模型

rocm3d 的产物是一个 **ROCm-ready 的模型 repo**（如 `ZJLi2013/TRELLIS.2`）。把它接进来：

1. **定位 repo**：优先 env var（如 `MYMODEL_REPO_PATH`），其次搜索常见路径，再次构造参数 `repo_path=`。
   不要写死绝对路径（参考 `trellis2_backend.py` 的 `_find_trellis2_repo()`）。
2. **跑通推理**：在 `generate()` 里把 repo 加进 `sys.path`、加载 pipeline、推理拿到几何，转成
   `trimesh.Trimesh`。ROCm 相关的环境开关（如 `FLASH_ATTENTION_TRITON_AMD_ENABLE`）在这里 setdefault。
3. **写清 `info`**：`rocm_status` / `min_vram_gb` / `install_hint` 决定 `list_backend_info()` 给用户的
   安装指引；ROCm 部署细节进 [rocm-setup.md](rocm-setup.md)。

RocRecon 只 **使用** rocm3d 移植好的模型，不在本仓库做移植本身。

## 3. 设计约束（为什么这么切）

- **后端只产 trimesh**：缩放到 `target_size_m`、按密度估质量、生成碰撞体、写 URDF 和
  `generation.json` 全在 `produce.py`。所有后端共享**同一产物契约**，下游（RoboSmith 等）不感知后端差异。
- **重依赖一律 lazy import**：`torch`、模型 pipeline、native 扩展不要在模块顶层 import——
  保持核心包只 `trimesh + numpy`，`import rocrecon` 不拉 GPU 栈，也不会因为某个后端没装而崩。
- **canonical frame 在 produce 层注入**（prompt 约束），不在各后端重复。
- **注册即插拔**：`@register_backend` + `_discover_builtins`，缺依赖的后端 import 失败时被静默跳过，
  不影响其他后端。

## 4. 扩展性与最终目标

当前后端接口是 **prompt 驱动**（`generate(prompt, ...)`），即 generation-shaped——这是现阶段
RocRecon 只做 object-level **gen3d** 的直接体现。

最终要解决的是 **real2sim**：让仿真资产/场景**忠实还原真实世界**，而不是「看起来合理的生成物」。
真实重建的输入是**采集数据**（多视图图像 / 视频 / RGB-D / 点云 / 扫描），不是一句 prompt、一张图。

因此架构上要把「mesh 的来源」抽象出来，让两类来源复用同一条 mesh → sim-ready 下游：

```
generation backend     prompt / image  ─┐
reconstruction backend captures(单物体) ─┼─►  trimesh ─► mesh_to_urdf ─► 资产目录契约（统一）
scene reconstruction   captures(场景)   ─┘                              （+ 场景布局/多物体）
```

- 现在：`produce.generate_asset(prompt, ...)`（generation 路径）。
- 将来：`reconstruct_asset(captures, ...)`（单物体重建）、`reconstruct_scene(captures, ...)`
  （场景级 real2sim，输出多物体布局 + 结构），共用 `mesh_to_urdf` 与产物契约。

对应 README 的 Next Step：先补单物体真实重建，再补场景级 real2sim。新增后端时按本文契约写，
就能平滑接入这条演进路线。

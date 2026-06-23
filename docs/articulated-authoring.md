# 铰接资产创作（Articraft）

铰接资产（抽屉柜、门、盖子等）的 mesh + URDF + 关节运动学由
[Articraft](https://github.com/mattzh72/articraft) 创作，产出**自包含 URDF**（primitive 内联几何，
可直接 `gs.morphs.URDF` 加载）。本文是可复现的创作流程；产出的 URDF 交给下游消费者做 onboarding
（语义标注、audit、validation），关节运动学唯一真相是 URDF，不复制进 metadata。

## 1. 环境（一次性）

Articraft 用 uv 安装，无需 sudo：

```bash
# uv -> ~/.local/bin（curl -LsSf https://astral.sh/uv/install.sh | sh）
git clone --depth 1 https://github.com/mattzh72/articraft.git ~/robot/articraft
cd ~/robot/articraft && uv sync --frozen --group dev   # 拉齐 cadquery / trimesh / python-fcl / ...
```

调用一律走 login shell 或先 `export PATH="$HOME/.local/bin:$PATH"`，否则 `uv` 不在 PATH。

## 2. SDK 创作约定

- 在 `model.py` 里实现 `build_object_model() -> ArticulatedObject`、`run_tests() -> TestReport`、
  顶层 `object_model = build_object_model()`（脚本契约，见 articraft `sdk/_docs/common/00_quickstart.md`）。
- 几何单位米；`Box` / `Sphere` / `Cylinder` 等 primitive 直接编译成 URDF 内联几何，**不产 mesh 文件**，
  资产自包含、最适合直接喂 Genesis。若需要 mesh OBJ 才用 `mesh_from_geometry(...)`。
- 关节用 `model.articulation(name, ArticulationType.PRISMATIC|REVOLUTE, parent, child, origin, axis, motion_limits)`；
  `axis` 是单位向量，prismatic 正向沿 `+axis` 平移、revolute 按右手定则。
- `compile` 自带 QC：model validity、单 root、mesh、孤立 part / 几何岛、**当前位姿真实 3D 重叠**。
  嵌套滑动配合（抽屉在柜体内）用 `expect_within`(非运动轴) + 位姿对比证明滑出方向，不要默认 `allow_overlap`。
- **可触 / 可抓部件拆成独立 fixed-joint link（碰撞规划的关键约定）**：把手、旋钮、拉手等「机器人有意接触」
  的部件，不要和被操作体本体（抽屉前脸 / 柜门面板 / 托盘）放在同一个 link，而是单独建一个 part、用
  `ArticulationType.FIXED` 接到本体上（`origin` 取 identity → 世界坐标不变）。例：抽屉的
  `base / drawer(去掉 handle) / drawer_handle(独立 fixed link)` 三链结构。
  动机：碰撞规划的有意接触豁免是**按 link 粒度**做的——本体该被避开、只有可触部件该被允许接触；
  同 link 时只能整条链一刀切，拆开后才能「只豁免可触 link、本体仍当硬障碍」。
- 把可触部件**尽量伸出本体包络**（如把手用 neck 撑离面板），给规划器留无碰撞 approach 余量。
  贴本体的把手即使拆了 link，抓取位姿仍可能落在本体 clearance 带内，需消费侧用 pre-contact standoff 兜底。

## 3. 端到端命令（手写 model.py，无需 LLM key）

```bash
# 全程：bash -lc 'cd ~/robot/articraft && <cmd>'
uv run articraft external init --agent cursor --model-id <id> --thinking-level high "<prompt>"
# -> 打印 record_id 与 active model.py 路径 revisions/rev_000001/model.py
# 把本地写好的 model.py 传到该路径
uv run articraft external check    data/records/<id>     # status=success failures=0 即通过
uv run articraft external finalize data/records/<id>
uv run articraft compile --target full data/records/<id> # 产出 model.urdf（含 inline 几何）
# materialization: data/cache/record_materialization/<id>/model.urdf
```

## 4. 产出与交接

产出：

- `model.urdf` — 自包含 primitive 几何与碰撞体，可直接 `gs.morphs.URDF` 加载。
- `model.py` — 创作源（provenance）。
- `assets/meshes/`（可选）— 仅当用了 `mesh_from_geometry(...)`。

交给消费者（如 RoboSmith）onboarding：补语义薄标注（任务关节、可抓 link、初始关节状态、upright、
metric_scale、tags），再走其 audit / validation gate。关节运动学只读 URDF。

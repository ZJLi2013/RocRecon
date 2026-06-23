# 资产生成指南：canonical frame 契约、prompt 指南、产物契约

RocRecon 的产物要直接进仿真，因此生成阶段就要把「机器人能用」的约束注入进去。
本文说明三件事：生成时的 canonical frame 契约、prompt 写法、以及产物目录契约。

---

## 1. Canonical frame 生成契约

下游不应该相信下载或生成 mesh 的原始 local axes：原点、up axis、front axis、单位和默认
姿态常常不统一。为减少下游 onboarding 的人工修正，RocRecon 在**生成时**就向 prompt 注入
canonical asset frame 约束：

```text
物体直立摆放；+Z 为语义 up；适用时 +X 为语义 front；
物体居中、原点干净；mesh 为米制尺度。
```

对应 `rocrecon.produce._with_canonical_asset_constraint`，会自动附加到 prompt（已包含时不重复）。

约定的语义坐标分层：

```text
mesh frame      资产文件里的原始作者坐标，不直接承载任务语义
object frame    canonical object frame，例如 +Z 为物体 up、+X 为 front
scene frame     由消费者（仿真/场景层）拥有，负责桌面、机器人、相机和摆放
```

RocRecon 负责让产物**尽量落在 canonical object frame**；它不写、也不保证任务级姿态验证
（如 “standing mug 的 upright”）——那是消费者的 onboarding/QA 职责。产物里的 `generation.json`
只记录生成溯源，不声明 `verified=true` 的任务姿态。

> 注意：canonical frame 是「生成时的努力目标」，不是「已验证的任务姿态」。物理稳定姿态
> （物体在平面上自然停住）与任务语义正放是两回事，后者需要消费者做 visual QA。

---

## 2. Prompt 指南

- **几何/抓取友好**：优先生成尺寸适合平行夹爪、桌面姿态稳定、语义清楚的物体；避免过大、
  过薄、过宽、细长高重心，以及透明/镜面/软体/线缆/布料等视觉或物理建模困难的对象。
- **canonical frame**：无需手写，`generate_asset` 会自动注入（见 §1）。如确需自定义，
  prompt 里包含 “canonical asset frame” 或 “+Z is semantic up” 即可跳过自动附加。
- **避免品牌与文字**：生成 generic object，不要带真实品牌或可读文字。
  例：医疗方向用 `small amber medicine bottle, no label`、`generic white medicine box`、
  `small lab reagent bottle`，而不是带 logo/标签的真实产品。

---

## 3. 产物目录契约

`generate_asset(...)` 在 `output_dir` 下产出：

```text
<output_dir>/
├── model.urdf        # 可仿真 URDF（visual + collision 两类 link）
├── visual.glb        # 视觉 mesh（有纹理时为 GLB；无纹理时 visual.obj）
├── collision.obj     # 凸包 / 简化后的碰撞 mesh
├── reference.png     # 输入参考图（如提供 image_path）
└── generation.json   # 溯源清单：name / prompt / backend / model_name / target_size_m
                      #          / density_kg_m3 / texture / created_at / 耗时
```

要点：

- `visual` 与 `collision` 文件都会产出；`mesh_to_urdf` 负责缩放到 `target_size_m`、按
  `density_kg_m3` 估算质量（或用传入的 `mass_kg` 覆盖）、生成碰撞体。
- RocRecon **不写** `metadata.json`——那是消费者 catalog 步骤的产物，schema 由消费者拥有，
  以此保证 RocRecon 零下游依赖。
- 消费者（如 RoboSmith）在此目录之上做 onboarding：写 `metadata.json`、跑 audit、
  人工 upright QA、小批量 validation、定资产状态。这条 onboarding 主干属于消费者，不在 RocRecon。

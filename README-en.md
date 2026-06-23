# RocRecon

> [中文](README.md) | English

**The real2sim asset side of the RocRobSim platform — generation and reconstruction of all sim-ready assets.**

Capability spans **granularity (object → scene) × method (generation / reconstruction)**:

| Scope | Generation | Reconstruction |
| --- | :---: | :---: |
| Object · rigid | ✅ | ◻ |
| Object · articulated | ✅ | ◻ |
| Object · soft (cloth / fabric…) | ◻ | ◻ |
| Scene (street block / kitchen / living room…) | ◻ | ◻ |

✅ available ｜ ◻ planned. Generation = prompt / image → asset; reconstruction = real capture (RGB-D / video / scan) → asset.
Scene reconstruction targets NuRec-class capability: turn a whole street block / kitchen / living room into a directly simulatable environment.

It is a pure *producer*: it only writes files and has **no dependency on any
downstream consumer** (asset library, SDG data engine, etc.). Consumers ingest
the produced directory through their own catalog/metadata step.

## Where RocRecon sits

```
rocm3d          (ROCm enablement: make open-source 3D-gen models run on AMD GPUs)
   │  enables
   ▼
RocRecon        (real2sim pipeline: prompt/image -> sim-ready URDF asset)   <-- this repo
   │  produces asset dirs
   ▼
RoboSmith       (SDG data engine: consume assets + tasks -> training data)
```

- **rocm3d** is a ROCm-compatibility skill set for porting generation models.
  RocRecon *uses* ROCm-ready models; it does not port them.
- **RoboSmith** consumes RocRecon output but does not generate assets.


## Install

```bash
pip install -e .            # core (trimesh + numpy)
pip install -e ".[gen]"     # + torch / pillow for running generation backends
```

Generation backends additionally require the corresponding model repos on disk
(e.g. TRELLIS.2, Hunyuan3D, TripoSG). For the ROCm environment / model setup see
[docs/rocm-setup.md](docs/rocm-setup.md), and inspect each backend's hint:

```python
import rocrecon
for info in rocrecon.list_backend_info():
    print(info.name, info.install_hint)
```

## Usage

```python
import rocrecon

# Produce a sim-ready asset directory from an image (TRELLIS.2 needs image_path)
out = rocrecon.generate_asset(
    "red ceramic mug",
    output_dir="assets/red_mug",
    backend="trellis2",
    image_path="mug.png",
    target_size_m=0.1,
)
# out/ now contains: model.urdf, visual.glb (or .obj), collision.obj,
#                    reference.png, generation.json
```

Convert an existing mesh without running a backend:

```python
import trimesh
from rocrecon import mesh_to_urdf

mesh = trimesh.load("chair.glb", force="mesh")
mesh_to_urdf(mesh, "assets/chair", name="chair", target_size_m=0.8, mass_kg=3.0)
```

## Output contract

A produced asset directory contains:

| File | Purpose |
| --- | --- |
| `model.urdf` | Sim-ready URDF (visual + collision links) |
| `visual.glb` / `visual.obj` | Visual mesh (GLB when textured) |
| `collision.obj` | Convex / simplified collision mesh |
| `reference.png` | Input reference image (if provided) |
| `generation.json` | Provenance manifest (prompt, backend, model, timing) |

Consumers add their own `metadata.json` / catalog entry on top of this.
For the canonical-frame contract and prompt guidance, see
[docs/asset-generation.md](docs/asset-generation.md).

## Backends

| Backend | Model | ROCm status |
| --- | --- | --- |
| `trellis2` | Microsoft TRELLIS.2-4B (image-to-3D, PBR) | verified (MI300X) |
| `hunyuan3d` | Tencent Hunyuan3D | community fork |
| `triposg` | TripoSG | verified (MI300X) |


## Next Step

Fill in the ◻ cells above, in order:

1. Object reconstruction (real RGB-D / video / scan → single-object asset)
2. Soft-body generation (cloth / fabric and other deformables)
3. Scene reconstruction (NuRec-class whole-scene real2sim: street block / kitchen / living room → simulatable environment)


## Docs

- [docs/asset-generation.md](docs/asset-generation.md) — canonical-frame contract, prompt guidance, output contract
- [docs/articulated-authoring.md](docs/articulated-authoring.md) — articulated asset authoring (Articraft → self-contained URDF)
- [docs/rocm-setup.md](docs/rocm-setup.md) — TRELLIS.2 / generation backend setup on ROCm
- [docs/extending-backends.md](docs/extending-backends.md) — developer guide: add a backend (incl. bringing in rocm3d models), extensibility & end goal

## References

- TRELLIS.2 — [microsoft/TRELLIS](https://github.com/microsoft/TRELLIS) (ROCm fork [ZJLi2013/TRELLIS.2](https://github.com/ZJLi2013/TRELLIS.2))
- Hunyuan3D-2 — [Tencent-Hunyuan/Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)
- Articraft — [mattzh72/articraft](https://github.com/mattzh72/articraft)
- Objaverse — [allenai/objaverse-xl](https://github.com/allenai/objaverse-xl)

# 生成后端的 ROCm 部署（TRELLIS.2）

> 本文是把 image-to-3D 生成后端跑在 AMD ROCm GPU 上的可复现流程，以 TRELLIS.2 为主。
> Hunyuan3D / TripoSG 同理：先按其官方说明拿到 ROCm-ready 的 repo，再用 `rocrecon.get_backend(...)` 调用。
> （历史上这套流程在 MI300X / MI350X + ROCm 6.4 / 7.2 上验证过。）

TRELLIS.2 用于 image-to-3D 资产生成。把 TRELLIS.2 repo、Hugging Face cache、
输入图像和生成产物都放在**宿主机持久化目录**，不要只留在临时容器层里。

```bash
ROOT=${ROOT:-$HOME/robot}
TRELLIS2=$ROOT/TRELLIS.2
HF_CACHE=$ROOT/HFCache

cd "$ROOT"
git clone -b rocm https://github.com/ZJLi2013/TRELLIS.2.git --recursive "$TRELLIS2"
mkdir -p "$ROOT/trellis2_inputs" "$HF_CACHE"
```

`HF_CACHE` 用于 TRELLIS.2 与 DINOv3 的模型权重，应当在容器重建后仍然存活，并被该节点上
所有 TRELLIS.2 运行共享。

在 MI350X / ROCm 7.2 节点上，用一个能看到 GPU 的镜像，然后在关闭 build isolation 的情况下
安装 ROCm 兼容的 TRELLIS.2 native 扩展：

```bash
docker run -it --name rocrecon_trellis2 \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  --security-opt seccomp=unconfined --ipc=host --shm-size=32g \
  -e HIP_VISIBLE_DEVICES=0 \
  -e ROCR_VISIBLE_DEVICES=0 \
  -e CUDA_VISIBLE_DEVICES=0 \
  -e GPU_ARCHS=gfx942 \
  -e PYTORCH_ROCM_ARCH=gfx942 \
  -e FLASH_ATTENTION_TRITON_AMD_ENABLE=TRUE \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e OPENCV_IO_ENABLE_OPENEXR=1 \
  -e TRELLIS2_REPO_PATH=/workspace/TRELLIS.2 \
  -e HF_HOME=/root/.cache/huggingface \
  -v "$TRELLIS2":/workspace/TRELLIS.2 \
  -v "$ROOT/trellis2_inputs":/workspace/trellis2_inputs \
  -v "$HF_CACHE":/root/.cache/huggingface \
  <rocm-pytorch-image> \
  bash
```

容器内安装 native 扩展：

```bash
cd /workspace/TRELLIS.2
apt-get update
apt-get install -y git libjpeg-dev build-essential ninja-build

function sudo(){ "$@"; }
. ./setup.sh --basic

FLASH_ATTENTION_TRITON_AMD_ENABLE=TRUE \
  python -m pip install flash-attn --no-build-isolation

python -m pip install \
  "git+https://github.com/ZJLi2013/nvdiffrast.git@rocm" \
  --no-build-isolation

rm -rf /tmp/extensions && mkdir -p /tmp/extensions
git clone -b rocm https://github.com/ZJLi2013/CuMesh.git /tmp/extensions/CuMesh --recursive
cd /tmp/extensions/CuMesh && GPU_ARCHS=gfx942 python -m pip install . --no-build-isolation

git clone -b rocm https://github.com/ZJLi2013/FlexGEMM.git /tmp/extensions/FlexGEMM --recursive
python -m pip install /tmp/extensions/FlexGEMM --no-build-isolation

cp -r /workspace/TRELLIS.2/o-voxel /tmp/extensions/o-voxel
python -m pip install /tmp/extensions/o-voxel --no-build-isolation --no-deps

# TRELLIS.2 目前需要 bleeding-edge Transformers 里的 DINOv3 类。
python -m pip install --upgrade "git+https://github.com/huggingface/transformers.git"
```

加载 pipeline 前先登录 Hugging Face。DINOv3 image encoder 是 gated 模型，token 必须有
`facebook/dinov3-vitl16-pretrain-lvd1689m` 的访问权限。这会把认证/缓存元数据写进宿主机挂载的
`HF_CACHE`。

```bash
python - <<'PY'
import os
from huggingface_hub import login, whoami

login(token=os.environ["HF_TOKEN"], add_to_git_credential=False)
print("HF login:", whoami().get("name"))
PY

du -sh /root/.cache/huggingface
```

扩展导入冒烟，并确认容器只看到一块 GPU：

```bash
python - <<'PY'
import os, sys, torch

sys.path.insert(0, os.environ["TRELLIS2_REPO_PATH"])
print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name())
print("visible GPU count:", torch.cuda.device_count())

import nvdiffrast.torch as dr
import cumesh, flex_gemm, o_voxel
from trellis2.pipelines import Trellis2ImageTo3DPipeline

print("TRELLIS2_READY")
PY
```

模型加载冒烟（这一步会把 TRELLIS.2、RMBG、DINOv3 权重下载进持久化 HF cache）：

```bash
python - <<'PY'
import os, sys, torch

sys.path.insert(0, os.environ["TRELLIS2_REPO_PATH"])
from trellis2.pipelines import Trellis2ImageTo3DPipeline

pipeline = Trellis2ImageTo3DPipeline.from_pretrained("microsoft/TRELLIS.2-4B")
pipeline.cuda()
print("TRELLIS2_MODEL_LOADED", torch.cuda.get_device_name())
PY
```

需要的 gated 依赖：

```text
facebook/dinov3-vitl16-pretrain-lvd1689m
```

冒烟通过后，保存 ready 镜像，避免新容器重复编译扩展：

```bash
docker commit rocrecon_trellis2 rocrecon:trellis2-rocm72-ready
```

环境就绪后，即可用 RocRecon 产出资产目录：

```python
import rocrecon

rocrecon.generate_asset(
    "red ceramic mug",
    output_dir="assets/red_mug",
    backend="trellis2",
    image_path="/workspace/trellis2_inputs/mug.png",
)
```

产物目录写到哪里由 `output_dir` 决定，由下游消费者（如 RoboSmith 的资产库）摄入。

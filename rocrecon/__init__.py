"""RocRecon: real2sim asset generation pipeline (prompt/image -> sim-ready URDF).

Produces sim-ready asset directories from 3D generation backends. Pure producer:
writes URDF + meshes + a generation manifest, with no dependency on any
downstream consumer (asset library, SDG engine, etc.).
"""

from rocrecon.backend import (
    BackendInfo,
    GenBackend,
    get_backend,
    list_backend_info,
    list_backends,
    register_backend,
)
from rocrecon.mesh_to_urdf import mesh_to_urdf
from rocrecon.produce import generate_asset

__all__ = [
    "BackendInfo",
    "GenBackend",
    "get_backend",
    "list_backend_info",
    "list_backends",
    "register_backend",
    "mesh_to_urdf",
    "generate_asset",
]

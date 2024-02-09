import importlib
import os

from pyrenode3.loader import RenodeLoader

if "PYRENODE_SKIP_LOAD" not in os.environ:
    if (pkg := os.environ.get("PYRENODE_ARCH_PKG")) is not None:
        RenodeLoader.from_arch(pkg)

    elif (pkg := os.environ.get("PYRENODE_BUILD_DIR")) is not None:
        RenodeLoader.from_mono_build(pkg)

    if not RenodeLoader().is_initialized:
        msg = "Renode not found. Please set PYRENODE_ARCH_PKG to the location of Renode Arch package."
        raise ImportError(msg)

    # this prevents circular imports
    importlib.import_module("pyrenode3.wrappers")

    from pyrenode3.conversion import interface_to_class
    from pyrenode3.rpath import RPath

__all__ = [
    "RPath",
    "interface_to_class",
    "wrappers",
]

import importlib
import logging
import os

from pyrenode3.loader import RenodeLoader

if "PYRENODE_SKIP_LOAD" not in os.environ:
    runtime = os.environ.get("PYRENODE_RUNTIME", "mono")

    if runtime not in ["mono", "coreclr"]:
        raise ImportError(f"Runtime '{runtime}' not supported")

    if os.environ.get("PYRENODE_PKG") and os.environ.get("PYRENODE_BUILD_DIR"):
        raise ImportError(
            "Both PYRENODE_PKG and PYRENODE_BUILD_DIR are set. Please unset one of them."
        )

    if package := os.environ.get("PYRENODE_PKG"):
        if runtime == "mono":
            RenodeLoader.from_mono_arch_pkg(package)
        elif runtime == "coreclr":
            raise ImportError("Using dotnet package is not supported.")

    elif build_dir := os.environ.get("PYRENODE_BUILD_DIR"):
        if runtime == "mono":
            RenodeLoader.from_mono_build(build_dir)
        elif runtime == "coreclr":
            RenodeLoader.from_net_build(build_dir)

    if not RenodeLoader().is_initialized:
        msg = (
            "Renode not found. Please set PYRENODE_ARCH_PKG to the location of Renode Arch package."
            "Set PYRENODE_PKG to the location of Renode package or PYRENODE_BUILD_DIR to the"
            "location of Renode build directory."
        )
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

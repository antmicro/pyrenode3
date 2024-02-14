import importlib
import logging

from pyrenode3.loader import RenodeLoader
from pyrenode3 import env


if not env.pyrenode_skip_load:
    runtime = env.pyrenode_runtime

    if runtime not in ["mono", "coreclr"]:
        raise ImportError(f"Runtime '{runtime}' not supported")

    if env.pyrenode_pkg and env.pyrenode_build_dir:
        raise ImportError(
            f"Both {env.PYRENODE_PKG} and {env.PYRENODE_BUILD_DIR} are set. "
            "Please unset one of them."
        )

    if env.pyrenode_pkg:
        if runtime == "mono":
            RenodeLoader.from_mono_arch_pkg(env.pyrenode_pkg)
        elif runtime == "coreclr":
            raise ImportError("Using dotnet package is not supported.")

    elif env.pyrenode_build_dir:
        if runtime == "mono":
            logging.warning("Using mono with Renode built from sources might not work correctly.")
            RenodeLoader.from_mono_build(env.pyrenode_build_dir)
        elif runtime == "coreclr":
            RenodeLoader.from_net_build(env.pyrenode_build_dir)

    if not RenodeLoader().is_initialized:
        msg = (
            f"Renode not found. Please set {env.PYRENODE_PKG} to the location of Renode package or "
            f"{env.PYRENODE_BUILD_DIR} to the location of Renode build directory."
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

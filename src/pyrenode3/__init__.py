import importlib
import logging

from pyrenode3.loader import RenodeLoader
from pyrenode3 import env


if not env.pyrenode_skip_load:
    runtime = env.pyrenode_runtime

    if runtime not in ["mono", "coreclr"]:
        raise ImportError(f"Runtime {runtime!r} not supported")

    if sum(map(bool, (env.pyrenode_pkg, env.pyrenode_build_dir, env.pyrenode_bin))) > 1:
        raise ImportError(
            f"Multiple of {env.PYRENODE_PKG}, {env.PYRENODE_BUILD_DIR}, {env.PYRENODE_BIN} are set. Please unset all but one of them."
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

    elif env.pyrenode_bin:
        if runtime == "mono":
            raise ImportError("Using mono portable binary is not supported.")
        elif runtime == "coreclr":
            RenodeLoader.from_net_bin(env.pyrenode_bin)

    if not RenodeLoader().is_initialized:
        msg = (
            f"Renode not found. Please set {env.PYRENODE_PKG} to the location of Renode package "
            f"or {env.PYRENODE_BUILD_DIR} to the location of Renode build directory, "
            f"or {env.PYRENODE_BIN} to the location of Renode portable binary."
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

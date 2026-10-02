import importlib
import logging
import os
import threading

from pyrenode3.loader import RenodeLoader
from pyrenode3 import env

logger = logging.getLogger(__name__)

def get_renode_path_from_env():
    paths = []

    if env.pyrenode_path:
        paths.append((env.PYRENODE_PATH, env.pyrenode_path))

    for var in env.PYRENODE_PATH_ALIASES:
        value = os.environ.get(var)
        if value:
            logger.warning(f"{var} is deprecated. Please use {env.PYRENODE_PATH} instead.")
            paths.append((var, value))

    if not paths:
        return None

    distinct_paths = set(path for _, path in paths)
    if len(distinct_paths) > 1:
        envs = ", ".join(var for var, _ in paths)
        raise ImportError(f"Multiple Renode paths are set via {envs}. Please set only {env.PYRENODE_PATH}.")

    return paths[0][1]


if not env.pyrenode_skip_load:
    renode_path = get_renode_path_from_env()

    if renode_path:
        RenodeLoader.from_path(renode_path)
    else:
        RenodeLoader.from_installed()

    if not RenodeLoader().is_initialized:
        msg = (
            f"Renode not found. Please do one of following actions:\n"
            f"   - install Renode from a package\n"
            f"   - set {env.PYRENODE_PATH} to the location of the Renode package, build directory or portable binary\n"
        )
        raise ImportError(msg)

    from System.Threading import Thread
    Thread.CurrentThread.Name = threading.current_thread().name

    # this prevents circular imports
    importlib.import_module("pyrenode3.wrappers")

    from pyrenode3.conversion import interface_to_class
    from pyrenode3.rpath import RPath

__all__ = [
    "RPath",
    "interface_to_class",
    "wrappers",  # type: ignore -- this is imported dynamically
]

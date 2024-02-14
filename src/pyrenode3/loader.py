import glob
import logging
import os
import pathlib
import sys
import tarfile
import tempfile
from contextlib import contextmanager
from typing import Union

from pythonnet import load as pythonnet_load

from pyrenode3 import env
from pyrenode3.singleton import MetaSingleton


class InitializationError(Exception):
    ...


class RenodeLoader(metaclass=MetaSingleton):
    """A class used for loading Renode DLLs, platforms and scripts from various sources."""

    def __init__(self):
        self.__initialized = False
        self.__bin_dir = None
        self.__renode_dir = None

    @property
    def is_initialized(self):
        """Check if Renode is loaded."""
        return self.__initialized

    @property
    def root(self) -> "pathlib.Path":
        """Get path to the Renode's root."""
        if self.__renode_dir is None:
            msg = "RenodeLoader wasn't initialized"
            raise InitializationError(msg)

        return self.__renode_dir

    @property
    def binaries(self) -> "pathlib.Path":
        """Get path to the directory containing Renode's DLLs."""
        if self.__bin_dir is None:
            msg = "RenodeLoader wasn't initialized"
            raise InitializationError(msg)

        return self.__bin_dir

    @classmethod
    def from_mono_arch_pkg(cls, path: "Union[str, pathlib.Path]"):
        """Load Renode from Arch package."""
        path = pathlib.Path(path)
        temp = tempfile.TemporaryDirectory()
        with tarfile.open(path, "r") as f:
            f.extractall(temp.name)

        renode_dir = pathlib.Path(temp.name) / "opt/renode"

        loader = cls()
        loader.__setup(
            renode_dir / "bin",
            renode_dir,
            runtime="mono",
            temp=temp,
            add_dlls=["Renode.exe"]
        )

        return loader

    @staticmethod
    def discover_bin_dir(renode_dir, runtime):
        if env.pyrenode_build_output:
            renode_build_dir = renode_dir / env.pyrenode_build_output

            if not renode_build_dir.exists():
                logging.critical(f"{renode_build_dir} doesn't exist.")
                sys.exit(1)
        else:
            default = "output/bin/Release"
            if runtime == "coreclr":
                default += "/net*"

            dirs = glob.glob(str(renode_dir / default))

            if len(dirs) != 1:
                logging.critical(
                    f"Can't determine Renode directory using the '{renode_dir / default}' pattern. "
                    f"Please specify its path (relative to {renode_dir}) in the "
                    f"{env.PYRENODE_BUILD_OUTPUT} variable."
                )
                sys.exit(1)

            renode_build_dir = pathlib.Path(dirs[0])

        logging.info(f"Using {renode_build_dir} as a directory with Renode binaries.")
        return renode_build_dir

    @classmethod
    def from_mono_build(cls, path: "Union[str, pathlib.Path]"):
        """Load Renode from Mono build."""
        renode_dir = pathlib.Path(path)
        loader = cls()
        loader.__setup(
            cls.discover_bin_dir(renode_dir, "mono"),
            renode_dir,
            runtime="mono",
            add_dlls=["Renode.exe"]
        )

        return loader

    @classmethod
    def from_net_build(cls, path: "Union[str, pathlib.Path]"):
        renode_dir = pathlib.Path(path)
        renode_bin_dir = cls.discover_bin_dir(renode_dir, "coreclr")

        # HACK: move libMonoPosixHelper.so to path where it is searched for
        src = renode_bin_dir / "runtimes/linux-x64/native/libMonoPosixHelper.so"
        dst = renode_bin_dir / "runtimes/linux-x64/lib/netstandard2.0/libMonoPosixHelper.so"
        if not dst.exists():
            src_path = os.path.relpath(src, dst.parent)
            logging.warning("libMonoPosixHelper.so is not in the expected location. Creating symlink.")
            logging.warning(f"{src_path} -> {dst}")
            os.symlink(src_path, dst)

        loader = cls()
        loader.__setup(
            renode_bin_dir,
            renode_dir,
            runtime="coreclr",
            add_dlls=["runtimes/linux-x64/lib/netstandard2.0/Mono.Posix.NETStandard.dll"],
        )

        return loader

    @contextmanager
    def in_root(self):
        last_cwd = os.getcwd()
        try:
            os.chdir(self.root)
            yield
        finally:
            os.chdir(last_cwd)

    def __load_runtime(self):
        params = {}
        if self.__runtime ==  "coreclr":
            # When using .NET Renode and the runtimeconfig.json file is present we should use that
            # to specify exactly the runtime that is expected.
            runtime_config = self.__bin_dir / "Renode.runtimeconfig.json"
            if runtime_config.exists():
                params["runtime_config"]  = runtime_config
            else:
                logging.warning(
                    "Can't find the Renode.runtimeconfig.json file. "
                    "Will use a default pythonnet runtime settings."
                )

        pythonnet_load(self.__runtime, **params)

    def __load_asm(self):
        # Import clr here, because it must be done after the proper runtime is selected.
        # If the runtime isn't loaded, the clr module loads the default runtime (mono) automatically.
        # It is an issue when we use non-default runtime, e.g. coreclr.
        import clr

        dlls = [*glob.glob(str(self.binaries / "*.dll"))]
        dlls.extend(self.__extra.get("add_dlls", []))

        for dll in dlls:
            clr.AddReference(str(self.binaries / dll))

    def __setup(self,
        bin_dir: "Union[str, pathlib.Path]",
        renode_dir: "Union[str, pathlib.Path]",
        runtime: str,
        **kwargs,
    ):
        if self.__initialized:
            msg = "RenodeLoader is already initialized"
            raise InitializationError(msg)

        self.__bin_dir = pathlib.Path(bin_dir).absolute()
        self.__renode_dir = pathlib.Path(renode_dir).absolute()
        self.__runtime = runtime
        self.__extra = kwargs

        self.__load_runtime()

        self.__load_asm()

        self.__initialized = True

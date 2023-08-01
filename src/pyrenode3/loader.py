import glob
import os
import pathlib
import tarfile
import tempfile
from contextlib import contextmanager
from typing import Union

import clr

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
    def from_arch(cls, path: "Union[str, pathlib.Path]"):
        """Load Renode from Arch package."""
        path = pathlib.Path(path)
        temp = tempfile.TemporaryDirectory()
        with tarfile.open(path, "r") as f:
            f.extractall(temp.name)

        renode_dir = pathlib.Path(temp.name) / "opt/renode"

        loader = cls()
        loader.__setup(renode_dir / "bin", renode_dir, temp=temp)

        return loader

    @classmethod
    def from_mono_build(cls, path: "Union[str, pathlib.Path]"):
        """Load Renode from Mono build."""
        renode_dir = pathlib.Path(path)
        loader = cls()
        loader.__setup(renode_dir / "output/bin/Release", renode_dir)

        return loader

    @contextmanager
    def in_root(self):
        last_cwd = os.getcwd()
        try:
            os.chdir(self.root)
            yield
        finally:
            os.chdir(last_cwd)

    def __load_asm(self):
        dlls = [
            *glob.glob(str(self.binaries / "*.dll")),
            "Renode.exe",
        ]

        for dll in dlls:
            clr.AddReference(str(self.binaries / dll))

    def __setup(self, bin_dir: "Union[str, pathlib.Path]", renode_dir: "Union[str, pathlib.Path]", **kwargs):
        if self.__initialized:
            msg = "RenodeLoader is already initialized"
            raise InitializationError(msg)

        self.__bin_dir = pathlib.Path(bin_dir).absolute()
        self.__renode_dir = pathlib.Path(renode_dir).absolute()
        self.__extra = kwargs

        self.__load_asm()

        self.__initialized = True

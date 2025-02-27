import glob
import json
import logging
import os
import pathlib
import re
import sys
import tarfile
import tempfile
import platform
from contextlib import contextmanager
from typing import Union
from subprocess import check_output, STDOUT

from pythonnet import load as pythonnet_load
from clr_loader.util.runtime_spec import DotnetCoreRuntimeSpec

from pyrenode3 import env
from pyrenode3.singleton import MetaSingleton


class InitializationError(Exception):
    ...


def ensure_symlink(src, dst, relative=False, verbose=False):
    if relative:
        src = os.path.relpath(src, dst.parent)
    try:
        dst.symlink_to(src)
    except FileExistsError:
        return
    if verbose:
        logging.warning(f"{dst.name} is not in the expected location. Created symlink.")
        logging.warning(f"{src} -> {dst}")

# Returns the runtime identifier (RID) of the current platform,
# only handle targets Renode supports
def get_RID():
    aarch64_names = set(("arm64", "aarch64"))
    if platform.machine() in aarch64_names:
        arch = "arm64"
    else:
        arch = "x64"
    kernel_name = platform.system()
    if kernel_name == "Linux":
        os = "linux"
    elif kernel_name == "Darwin":
        os = "osx"
    elif kernel_name == "Windows":
        os = "win"
    else:
        msg = "Operating system " + os + " not recognized"
        raise InitializationError(msg)
    return os + '-' + arch

def get_library_ext():
    kernel_name = platform.system()
    if kernel_name == "Linux":
        return ".so"
    elif kernel_name == "Darwin":
        return ".dylib"
    elif kernel_name == "Windows":
        return ".dll"
    else:
        msg = "Operating system " + os + " not recognize"
        raise InitializationError(msg)


def ensure_additional_libs(renode_bin_dir):
    # libMono.Unix does not exists on Windows, so just return empty if we are on Windows
    if platform.system() == "Windows":
        return []
    # HACK: move libMonoPosixHelper to path where it is searched for
    bindll_dir = renode_bin_dir / "runtimes" / get_RID()
    # Updating to Mono.Posix changed the name of this file
    # so we check for the new one, and fall back on the old one if it is not found
    lib_new = "libMono.Unix" + get_library_ext()
    lib_old = "libMonoPosixHelper" + get_library_ext()
    src_new = bindll_dir / "native" / lib_new
    src_old = bindll_dir / "native" / lib_old

    if src_new.exists():
        ensure_symlink(src_new, renode_bin_dir / lib_new, verbose=True)
        return [renode_bin_dir / "Mono.Posix.dll"]
    else:
        netstd_dir = bindll_dir / "lib/netstandard2.0"
        ensure_symlink(src_old, netstd_dir / lib_old, relative=True, verbose=True)
        return [netstd_dir / "Mono.Posix.NETStandard.dll"]



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

        pythonnet_load("mono")

        loader = cls()
        loader.__setup(
            renode_dir / "bin",
            renode_dir,
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

        pythonnet_load("mono")

        loader = cls()
        loader.__setup(
            cls.discover_bin_dir(renode_dir, "mono"),
            renode_dir,
            add_dlls=["Renode.exe"]
        )

        return loader

    @classmethod
    def from_net_pkg(cls, path: "Union[str, pathlib.Path]"):
        """Load Renode from dotnet package."""
        path = pathlib.Path(path)
        temp = tempfile.TemporaryDirectory()
        with tarfile.open(path, "r") as f:
            f.extractall(temp.name)

        renode_dirs = list(pathlib.Path(temp.name).glob("renode*"))
        if len(renode_dirs) > 1:
            logging.error(f"In {path} package should be exactly one directory. Found {len(renode_dirs)}.")
            sys.exit(1)

        renode_dir = renode_dirs[0]
        renode_bin_dir = renode_dir / "bin"

        additional_libs = ensure_additional_libs(renode_bin_dir)

        pythonnet_load("coreclr", runtime_config=renode_bin_dir / "Renode.runtimeconfig.json")

        loader = cls()
        loader.__setup(
            renode_bin_dir,
            renode_dir,
            temp=temp,
            add_dlls=additional_libs,
        )
        return loader

    @classmethod
    def from_net_build(cls, path: "Union[str, pathlib.Path]"):
        renode_dir = pathlib.Path(path)
        renode_bin_dir = cls.discover_bin_dir(renode_dir, "coreclr")

        additional_libs = ensure_additional_libs(renode_bin_dir)

        pythonnet_load("coreclr", runtime_config=renode_bin_dir / "Renode.runtimeconfig.json")

        loader = cls()
        loader.__setup(
            renode_bin_dir,
            renode_dir,
            add_dlls=additional_libs,
        )
        return loader

    @classmethod
    def from_net_bin(cls, path: "Union[str, pathlib.Path]"):
        """Load Renode from binary."""
        renode_bin = pathlib.Path(path)
        renode_dir = renode_bin.parent

        # As a side effect, executing the binary causes the embedded dlls to be extracted to:
        #     ~/.net/<executable name>/<executable hash>/
        # The location gets printed to stderr (or selected file) if suitable environment variables are set.
        out = check_output([renode_bin, "--version"], stderr=STDOUT, env=os.environ | {"COREHOST_TRACE": "1", "COREHOST_TRACEFILE": ""}, text=True)

        binaries = re.search(r"will be extracted to \[(.*)\] directory", out).group(1)
        binaries = pathlib.Path(binaries)

        # There should be *some* way to specify a dll PATH, but it does not 'just work' e.g. in runtimeconfig.json.
        # As a workaround, we create a directory hierarchy (can be anywhere, but we use ~/.net/...) like
        #     shared/Microsoft.NETCore.App/6.0.26/
        #         libclrjit.so
        #         libcoreclr.so
        #         libSystem.Native.so
        #         libSystem.Security.Cryptography.Native.OpenSsl.so
        #         Microsoft.CSharp.dll
        #         ...
        #         Microsoft.NETCore.App.deps.json
        # The DLLs are extracted, the .so libs are blended into the .text of the executable, so we ship them,
        # and the deps.json can be pretty much any deps.json file, so we use the extracted Renode.deps.json.

        # We need to find *some* runtime version, although 6.0.0 is 'good enough' if we find nothing else.
        # Luckily, deps.json has the runtime version info, and a list of system DLLs:
        # {
        #     "runtimeTarget": {
        #       "name": ".NETCoreApp,Version=v6.0/linux-x64",
        #       "signature": ""
        #     },
        #     "compilationOptions": {},
        #     "targets": {
        #       ".NETCoreApp,Version=v6.0": {},
        #       ".NETCoreApp,Version=v6.0/linux-x64": {
        #         "Renode/1.0.0": {
        #           "dependencies": {
        #             "AntShell": "1.0.0",
        #             ...
        #             "runtimepack.Microsoft.NETCore.App.Runtime.linux-x64": "6.0.26"
        #           },
        #           "runtime": {
        #             "Renode.dll": {}
        #           }
        #         },
        #         "runtimepack.Microsoft.NETCore.App.Runtime.linux-x64/6.0.26": {
        #           "runtime": {
        #             "Microsoft.CSharp.dll": {
        #               "assemblyVersion": "6.0.0.0",
        #               "fileVersion": "6.0.2623.60508"
        #             },
        #             "Microsoft.VisualBasic.Core.dll": { ... },
        #  }}}}}
        SYSTEM_RUNTIME = "runtimepack.Microsoft.NETCore.App.Runtime." + get_RID()
        LIB_EXT = get_library_ext()

        deps = json.load(open(binaries / "Renode.deps.json", "rb"))
        target = deps["targets"][deps["runtimeTarget"]["name"]]
        for lib, dlls in target.items():
            name, version = lib.split("/")
            if name == SYSTEM_RUNTIME:
                tfm_full = version
                system_dlls = list(dlls["runtime"])
                break
        else:
            tfm_full = "8.0.0"
            system_dlls = [dll.name for dll in binaries.glob("*.dll")]
            logging.warning(f"Could not find {SYSTEM_RUNTIME} in deps.json. "
                            f"Assuming framework version {tfm_full}.")

        runtime = binaries / "shared/Microsoft.NETCore.App" / tfm_full
        runtime.mkdir(parents=True, exist_ok=True)
        for lib in renode_dir.glob("*" + LIB_EXT):
            ensure_symlink(lib, runtime / lib.name)

        for lib in system_dlls:
            ensure_symlink(binaries / lib, runtime / lib, relative=True)

        if platform.system() == "Windows":
            ensure_symlink(renode_dir / "hostfxr.dll", binaries / "hostfxr.dll")
        else:
            ensure_symlink(renode_dir / ("libhostfxr" + LIB_EXT), binaries / ("libhostfxr" + LIB_EXT))
        ensure_symlink(binaries / "Renode.deps.json", runtime / "Microsoft.NETCore.App.deps.json", relative=True)

        loader = cls()
        loader.__renode_dir = renode_dir
        with loader.in_root():
            pythonnet_load("coreclr", dotnet_root=binaries, runtime_spec=DotnetCoreRuntimeSpec("Microsoft.NETCore.App", tfm_full, runtime))
        loader.__setup(binaries, renode_dir)

        return loader

    @classmethod
    def from_installed(cls):
        try:
            version = check_output(["renode", "--version"])
        except FileNotFoundError:
            return None

        # TODO: Determine the runtime based on version string.
        #       (But currently version string doesn't contain runtime information.)

        # XXX: Assume that Renode is installed in /opt/renode. Once it is possible to install Renode
        #      to different location this must be changed!
        renode_dir = pathlib.Path("/opt/renode")

        loader = cls()
        loader.__setup(
            renode_dir / "bin",
            renode_dir,
            # XXX: Assume Mono runtime. Currently only Mono version can be installed as package.
            runtime="mono",
            add_dlls=["Renode.exe"]
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

    def __load_asm(self):
        # Import clr here, because it must be done after the proper runtime is selected.
        # If the runtime isn't loaded, the clr module loads the default runtime (mono) automatically.
        # It is an issue when we use non-default runtime, e.g. coreclr.
        import clr

        dlls = [*self.binaries.glob("*.dll")]
        dlls.extend(self.__extra.get("add_dlls", []))

        for dll in dlls:
            fullpath = self.binaries / dll
            # We do not normally ship CoreLib (except portable), and it gets loaded by other dlls anyway, but loading it directly raises an error:
            # System.IO.FileLoadException: Could not load file or assembly 'System.Private.CoreLib, Version=6.0.0.0, Culture=neutral, PublicKeyToken=7cec85d7bea7798e'.
            # sni.dll, hostfxr.dll, and the _cor3.dll files only exists on Windows, and causes a BadImageFormatException if loaded directly
            if (fullpath.exists() and
                fullpath.name != "System.Private.CoreLib.dll" and
                fullpath.name != "sni.dll" and
                fullpath.name != "hostfxr.dll" and
                "_cor3.dll" not in fullpath.name):
                clr.AddReference(str(fullpath))

    def __setup(self,
        bin_dir: "Union[str, pathlib.Path]",
        renode_dir: "Union[str, pathlib.Path]",
        **kwargs,
    ):
        if self.__initialized:
            msg = "RenodeLoader is already initialized"
            raise InitializationError(msg)

        self.__bin_dir = pathlib.Path(bin_dir).absolute()
        self.__renode_dir = pathlib.Path(renode_dir).absolute()
        self.__extra = kwargs

        self.__load_asm()

        self.__initialized = True

import atexit
import glob
import json
import logging
import os
import pathlib
import re
import sys
import shutil
import tarfile
import tempfile
import platform
import zipfile
from contextlib import contextmanager
from typing import Union
from subprocess import check_output, STDOUT

from pythonnet import load as pythonnet_load
from clr_loader.util.runtime_spec import DotnetCoreRuntimeSpec

from pyrenode3 import env
from pyrenode3.singleton import MetaSingleton


class InitializationError(Exception):
    ...


DOTNET_ASSEMBLY_PREFIXES = (
    "Microsoft.",
    "System.",
    "coreclr.dll",
    "hostfxr.dll",
    "hostpolicy.dll",
    "libllvm-disas.dll",
    "msquic.dll",
    "RenodeWPF.dll",
    "sni.dll",
    # clr* is 'Common Language Runtime'
    "clr",
    # mscor* is 'Microsoft Common Object Runtime Library'
    "mscor",
    # icu* is 'International Components for Unicode'
    "icu",
)


def is_framework_assembly(path):
    name = path.name
    # sni.dll, hostfxr.dll, and the _cor3.dll files only exist on Windows, and cause a
    # BadImageFormatException if loaded directly
    return any(name.startswith(p) for p in DOTNET_ASSEMBLY_PREFIXES) or name.endswith("_cor3.dll")


def ensure_symlink(src, dst, relative=False, verbose=False):
    linktype = "symlink"
    try:
        target = src.absolute() if not relative else src
        # Remove the existing destination if it's a symlink to somewhere wrong
        if dst.resolve().absolute() not in (dst.absolute(), target):
            dst.unlink()

        dst.symlink_to(target)
    except FileExistsError:
        return
    except OSError:
        try:
            dst.hardlink_to(src)
            linktype = "hardlink"
        except FileExistsError:
            return
        except OSError:
            shutil.copy(src, dst)
            linktype = "copy"
    if verbose:
        logging.warning(f"{dst.name} is not in the expected location. Created {linktype}.")
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
        msg = "Operating system " + kernel_name + " not recognized"
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
        msg = "Operating system " + kernel_name + " not recognize"
        raise InitializationError(msg)


def ensure_additional_libs(renode_bin_dir):
    # libMono.Unix does not exists on Windows, so just return empty if we are on Windows
    if platform.system() == "Windows":
        return []
    # HACK: move libMonoPosixHelper to path where it is searched for
    bindll_dir = pathlib.Path("runtimes") / get_RID()
    # Updating to Mono.Posix changed the name of this file
    # so we check for the new one, and fall back on the old one if it is not found
    lib_new = "libMono.Unix" + get_library_ext()
    lib_old = "libMonoPosixHelper" + get_library_ext()
    src_new = bindll_dir / "native" / lib_new
    src_old = bindll_dir / "native" / lib_old

    if (renode_bin_dir / src_new).exists():
        ensure_symlink(src_new, renode_bin_dir / lib_new, relative=True, verbose=True)
        return [renode_bin_dir / "Mono.Posix.dll"]
    elif (renode_bin_dir / src_old).exists():
        netstd_dir = renode_bin_dir / bindll_dir / "lib/netstandard2.0"
        ensure_symlink(src_old, netstd_dir / lib_old, relative=True, verbose=True)
        return [netstd_dir / "Mono.Posix.NETStandard.dll"]
    return []


def choose_runtime_config(bin_dir: pathlib.Path) -> pathlib.Path:
    runtime_config = bin_dir / "Renode.runtimeconfig.json"
    if platform.system() != "Windows":
        return runtime_config
    runtime_config_wpf = bin_dir / "RenodeWPF.runtimeconfig.json"
    if runtime_config_wpf.exists():
        return runtime_config_wpf
    return runtime_config

class RenodeLoader(metaclass=MetaSingleton):
    """A class used for loading Renode DLLs, platforms and scripts from various sources."""

    def __init__(self):
        self.__initialized = False
        self.__bin_dir = None
        self.__renode_dir = None
        self.__additional_dlls = []

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

    @staticmethod
    def is_coreclr_bin_dir(path):
        return (path / "Renode.runtimeconfig.json").exists() and (path / "Renode.dll").exists()

    @staticmethod
    def is_self_contained_coreclr_bin_dir(path):
        try:
            with open(path / "Renode.runtimeconfig.json") as config_fp:
                config = json.load(config_fp)
        except (OSError, json.JSONDecodeError):
            return False

        return "includedFrameworks" in config.get("runtimeOptions", {})

    @staticmethod
    def discover_renode_dir(path, visited=None):
        path = pathlib.Path(path)
        if visited is None:
            visited = set()
        real_path = path.resolve()
        if real_path in visited:
            raise InitializationError(f"Cyclic directory structure detected while looking for Renode directory in {path}.")
        visited.add(real_path)

        if (path / "opt/renode").exists():
            return path / "opt/renode"

        if (
            (path / ".renode-root").exists()
            or RenodeLoader.is_coreclr_bin_dir(path)
            or RenodeLoader.is_coreclr_bin_dir(path / "bin")
            or (path / "output/bin/Release").exists()
            or (env.pyrenode_build_output and (path / env.pyrenode_build_output).exists())
        ):
            return path

        # Packages extract into a single top-level renode* directory. Also support
        # pointing PYRENODE_PATH at the parent of such an unpacked directory
        renode_dirs = []
        for candidate in path.glob("renode*/"):
            try:
                renode_dirs.append(RenodeLoader.discover_renode_dir(candidate, visited))
            except InitializationError:
                pass

        renode_dirs = list(dict.fromkeys(renode_dirs))

        if len(renode_dirs) == 1:
            return renode_dirs[0]
        if len(renode_dirs) > 1:
            raise InitializationError(
                f"In {path} package should be exactly one Renode directory. Found {len(renode_dirs)}."
            )

        raise InitializationError(f"Can't determine Renode directory in {path}.")

    @staticmethod
    def get_single_file_portable_bin(path):
        names = ["renode", "Renode"]
        if platform.system() == "Windows":
            names.append("Renode.exe")
        for name in names:
            candidate = path / name
            if candidate.is_file():
                return candidate
        return None

    @classmethod
    def from_path(cls, path: "Union[str, pathlib.Path]"):
        """Load Renode from any supported package, build directory or portable binary."""
        path = pathlib.Path(path)

        if path.is_file():
            if tarfile.is_tarfile(path) or zipfile.is_zipfile(path):
                return cls.from_pkg(path)
            return cls.from_net_bin(path)

        if path.is_dir():
            return cls.from_dir(path)

        if path.is_symlink():
            raise InitializationError(f"{path} is a broken symlink.")

        if path.exists():
            raise InitializationError(f"{path} is not a file or directory.")

        raise InitializationError(f"{path} doesn't exist.")

    @classmethod
    def from_dir(cls, path: "Union[str, pathlib.Path]"):
        """Load Renode from a directory, detecting the runtime from its layout."""
        renode_dir = cls.discover_renode_dir(path)

        if (renode_dir / "output/bin/Release").exists() or (
            env.pyrenode_build_output and (renode_dir / env.pyrenode_build_output).exists()
        ):
            renode_bin_dir = cls.discover_bin_dir(renode_dir)
            if cls.is_coreclr_bin_dir(renode_bin_dir):
                return cls.from_net_dir(renode_dir, renode_bin_dir)
            raise InitializationError(f"Can't determine Renode runtime layout in {renode_bin_dir}.")

        if cls.is_coreclr_bin_dir(renode_dir / "bin"):
            return cls.from_net_dir(renode_dir, renode_dir / "bin")

        if cls.is_coreclr_bin_dir(renode_dir):
            root = renode_dir.parent if renode_dir.name == "bin" else renode_dir
            return cls.from_net_dir(root, renode_dir)

        if portable_bin := cls.get_single_file_portable_bin(renode_dir):
            return cls.from_net_bin(portable_bin)

        raise InitializationError(f"Can't determine Renode runtime layout in {renode_dir}.")

    @classmethod
    def from_net_dir(cls, renode_dir, renode_bin_dir):
        additional_libs = ensure_additional_libs(renode_bin_dir)

        if cls.is_self_contained_coreclr_bin_dir(renode_bin_dir):
            load_params = {
                "entry_dll": str(renode_bin_dir / "Renode.dll"),
                "dotnet_root": str(renode_bin_dir),
            }
        else:
            load_params = {"runtime_config": str(choose_runtime_config(renode_bin_dir))}
        pythonnet_load("coreclr", **load_params)

        loader = cls()
        loader.__setup(
            renode_bin_dir,
            renode_dir,
            add_dlls=additional_libs,
        )
        return loader

    @staticmethod
    def discover_bin_dir(renode_dir) -> pathlib.Path:
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
    def from_pkg(cls, path: "Union[str, pathlib.Path]"):
        """Load Renode from a package."""
        path = pathlib.Path(path)
        temp = tempfile.mkdtemp()

        # On Windows due to .dll file locking the automatic cleanup might fail.
        # In that case the user should be notified that manual removal is necessary.
        def rm_temp():
            try:
                shutil.rmtree(pathlib.Path(temp))
            except:
                print(f"Automatic cleanup failed to remove temporary directory '{temp}'.", file=sys.stderr)

        atexit.register(rm_temp)

        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path, "r") as f:
                f.extractall(temp)
        else:
            with tarfile.open(path, "r") as f:
                f.extractall(temp)

        return cls.from_dir(temp)

    @classmethod
    def from_net_bin(cls, path: "Union[str, pathlib.Path]"):
        """Load Renode from binary."""
        renode_bin = pathlib.Path(path).resolve()
        renode_dir = renode_bin.parent

        # From 18.06.2026 Renode packages are not built as a 'SingleFile' package.
        # This means that .dll files are now located inside the package directory
        # instead of being packed into 'renode' executable.
        # To determine which package we are working with we can check if a common .dll is present.

        binaries = None
        if pathlib.Path(renode_dir / "System.dll").is_file():
            binaries = renode_dir
        else:
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
        native_libs_to_load = list(renode_dir.glob("*" + LIB_EXT))
        deps_file = binaries / "Renode.deps.json"

        with open(deps_file, "rb") as deps_fp:
            deps = json.load(deps_fp)

        target = deps["targets"][deps["runtimeTarget"]["name"]]
        for lib, dlls in target.items():
            name, version = lib.split("/")
            if name == SYSTEM_RUNTIME:
                # Patch in the libraries into deps.json so that they can be easily found, otherwise libhostfxr.so doesn't find them in newer versions of the runtime
                dlls["native"] = {lib.name: {} for lib in native_libs_to_load}
                tfm_full = version
                system_dlls = list(dlls["runtime"])
                break
        else:
            tfm_full = "8.0.0"
            system_dlls = [dll.name for dll in binaries.glob("*.dll")]
            logging.warning(f"Could not find {SYSTEM_RUNTIME} in deps.json. "
                            f"Assuming framework version {tfm_full}.")

        with open(deps_file, "w") as deps_fp:
            json.dump(deps, deps_fp)

        runtime = binaries / "shared/Microsoft.NETCore.App" / tfm_full
        runtime.mkdir(parents=True, exist_ok=True)
        for lib in native_libs_to_load:
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

        # XXX: Assume that Renode is installed in /opt/renode. Once it is possible to install Renode
        #      to different location this must be changed!
        renode_dir = pathlib.Path("/opt/renode")
        renode_bin_dir = renode_dir / "bin"
        runtime_config = choose_runtime_config(renode_bin_dir)
        if not runtime_config.exists():
            return None

        pythonnet_load("coreclr", runtime_config=str(runtime_config))

        loader = cls()
        loader.__setup(
            renode_bin_dir,
            renode_dir,
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
        import clr

        dlls = [*self.binaries.glob("*.dll")]
        dlls.extend(self.__additional_dlls)

        for dll in dlls:
            fullpath = self.binaries / dll
            # We do not normally ship CoreLib (except portable), and it gets loaded by other dlls anyway, but loading it directly raises an error:
            # System.IO.FileLoadException: Could not load file or assembly 'System.Private.CoreLib, Version=6.0.0.0, Culture=neutral, PublicKeyToken=7cec85d7bea7798e'.
            if (fullpath.exists() and
                not is_framework_assembly(fullpath)):
                # XXX(pkoscik): Workaround for AssemblyName behavior change in .NET >= 9.0.
                # In .NET 8, passing a full DLL path (with extension) to AssemblyName(string) raised
                # FileLoadException, which Python.NET relied on. In .NET 9, the same path is parsed as
                # a valid assembly name, breaking Python.NET's loading heuristic. Paths without extension
                # are valid in both runtimes.
                clr.AddReference(str(fullpath.with_suffix("")))

    def __setup(
        self,
        bin_dir: "Union[str, pathlib.Path]",
        renode_dir: "Union[str, pathlib.Path]",
        add_dlls=None,
    ):
        if self.__initialized:
            msg = "RenodeLoader is already initialized"
            raise InitializationError(msg)

        self.__bin_dir = pathlib.Path(bin_dir).absolute()
        self.__renode_dir = pathlib.Path(renode_dir).absolute()
        # Keep extracted package directories alive for as long as the loader exists.
        self.__additional_dlls = add_dlls or []

        self.__load_asm()

        self.__initialized = True

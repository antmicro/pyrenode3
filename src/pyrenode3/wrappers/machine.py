from Antmicro.Renode import Core
from Antmicro.Renode.Core.Extensions import FileLoaderExtensions
from Antmicro.Renode.PlatformDescription.UserInterface import PlatformDescriptionMachineExtensions

from pyrenode3 import wrappers
from pyrenode3.rpath import RPath
from pyrenode3.wrapper import Wrapper


class Machine(Wrapper):
    """Wrapper of ``Machine``."""

    def __init__(self, machine: "Core.Machine"):
        super().__init__(machine)

    @property
    def sysbus(self) -> "wrappers.Peripheral":
        """Get machine's system bus."""
        return wrappers.Peripheral(self.internal.SystemBus)

    def load_repl(self, location: str) -> None:
        """Load REPL file from URL, Renode's folder or local filesystem.

        Parameters
        ----------
        location : str
            path or url to `.repl` file
        """
        wrappers.Monitor().Machine = self.internal

        # LoadPlatformDescription uses the machine provided by Monitor
        with RPath.in_root():
            PlatformDescriptionMachineExtensions.LoadPlatformDescription(self.internal, RPath(location).path)

    def load_elf(self, location: str) -> None:
        """Load ELF file from URL or local filesystem.

        Parameters
        ----------
        location : str
            path or url to ELF file.
        """
        self.sysbus.internal.LoadELF(RPath(location).read_file_path)

    def load_binary(self, location: str, load_point: int) -> None:
        """Load binary from URL or local filesystem.

        Parameters
        ----------
        location : str
            path or url to binary file

        load_point : int
            load point
        """
        FileLoaderExtensions.LoadBinary(self.sysbus.internal, RPath(location).read_file_path, load_point)

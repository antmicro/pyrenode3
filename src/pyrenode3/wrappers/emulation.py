import itertools
from typing import Iterable, Iterator, Optional

from Antmicro.Renode.Core import EmulationManager, Machine

from pyrenode3 import wrappers
from pyrenode3.inits import EmulatorInit
from pyrenode3.singleton import MetaSingleton
from pyrenode3.wrapper import Wrapper


class Emulation(Wrapper, metaclass=MetaSingleton):
    """Wrapper of ``Emulation``."""

    def __init__(self):
        EmulatorInit()
        super().__init__()

    def __iter__(self) -> "Iterator[wrappers.Machine]":
        """Get iterator over Emulation's machines."""
        return (self.get_mach(name) for name in self.internal.Names)

    def __delattr__(self, name: str) -> None:
        """Remove selected machine."""
        if not self.rem_mach(name):
            raise AttributeError

    @property
    def internal(self):
        return EmulationManager.Instance.CurrentEmulation

    @property
    def externals(self):
        return wrappers.ExternalsManager()

    def clear(self) -> None:
        """Remove all machines and resets the emulation."""
        EmulationManager.Instance.Clear()

    def add_mach(self, name: "Optional[str]" = None) -> "Optional[wrappers.Machine]":
        """Create a new machine and adds it to the emulation.

        If no `name` is specified, a new one is generated automatically.
        """
        m = Machine()

        if name is None:
            for name in self._generate_machine_names():
                if self.internal.TryAddMachine(m, name):
                    return wrappers.Machine(m)

        if self.internal.TryAddMachine(m, name):
            return wrappers.Machine(m)

    def get_mach(self, name: str) -> "Optional[wrappers.Machine]":
        """Find selected machine in the emulation."""
        present, m = self.internal.TryGetMachineByName(name)

        if present:
            return wrappers.Machine(m)

    def rem_mach(self, name: str) -> bool:
        """Remove selected machine from the emulation."""
        return self.internal.TryRemoveMachine(name)

    def _elements(self) -> "Iterable[str]":
        return list(self.internal.Names)

    def _get(self, item: str):
        if (mach := self.get_mach(item)) is not None:
            return mach

        raise AttributeError

    @classmethod
    def _generate_machine_names(cls) -> "Iterator[str]":
        for i in itertools.count():
            name = f"machine{i}"
            yield name

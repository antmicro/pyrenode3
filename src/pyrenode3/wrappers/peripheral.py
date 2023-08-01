from typing import Iterator, Optional

from Antmicro.Renode.Peripherals import IPeripheral, IPeripheralExtensions

from pyrenode3 import wrappers
from pyrenode3.conversion import interface_to_class
from pyrenode3.wrapper import Wrapper


class Peripheral(Wrapper):
    """Wrapper of ``IPeripheral`` and its derivatives."""

    def __init__(self, peripheral: "IPeripheral"):
        super().__init__(interface_to_class(peripheral))

    def __iter__(self) -> "Iterator[Peripheral]":
        """Get iterator over peripheral's children."""
        return iter(self.__children.values())

    @property
    def name(self) -> Optional[str]:
        """Get peripheral's name."""
        present, name = self.mach.TryGetLocalName(self.internal)
        if present:
            return name

    @property
    def path(self) -> str:
        """Get peripheral's path (e.g. ``sysbus.uart0``)."""
        _, name = self.mach.TryGetAnyName(self.internal)
        return name

    @property
    def mach(self) -> "wrappers.Machine":
        """Get peripheral's parent :class:`Mach <Mach>`."""
        m = IPeripheralExtensions.GetMachine(self.internal)
        return wrappers.Machine(m)

    def get_child(self, name: str):
        """Get peripheral's child peripheral."""
        return self.__children[name]

    def _elements(self):
        return self.__children

    def _get(self, item):
        return self.get_child(item)

    @property
    def __children(self) -> "dict[str, Peripheral]":
        ps = (Peripheral(x) for x in self.mach.GetChildrenPeripherals(self.internal))
        return {p.name: p for p in ps if p.name is not None}

from typing import Iterable, Iterator, Optional

from Antmicro.Renode.Core import IExternal

from pyrenode3 import wrappers
from pyrenode3.conversion import interface_to_class
from pyrenode3.singleton import MetaSingleton
from pyrenode3.wrapper import Wrapper


class ExternalsManager(Wrapper, metaclass=MetaSingleton):
    """Wrapper of ``Emulation``'s ``ExternalsManager``."""

    def __init__(self):
        super().__init__()

    def __iter__(self) -> "Iterator[IExternal]":
        """Get iterator over ExternalManager's externals."""
        return (interface_to_class(x) for x in self.internal.Externals)

    @property
    def internal(self):
        return wrappers.Emulation().internal.ExternalsManager

    def get_external(self, item: str) -> "Optional[IExternal]":
        """Find external in ExternalsManager.

        Parameters
        ----------
        item : str
            external's name

        Returns
        -------
        Optional[Any]
            Found external or ``None``

        """
        present, result = self.internal.TryGetByName[IExternal](item)
        if not present:
            return None

        return interface_to_class(result)

    def _elements(self) -> "Iterable[str]":
        return list(self.internal.GetNames())

    def _get(self, item: str):
        return self.get_external(item)

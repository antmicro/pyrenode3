from functools import partial
from importlib import import_module
from itertools import chain
from typing import Any, Iterable, Optional

from Antmicro.Renode.Utilities import TypeManager


class Wrapper:
    """A class used for providing Python.NET objects with extension methods and helpers."""

    def __init__(self, internal=None):
        self.__internal = internal

    def __dir__(self) -> "Iterable[str]":
        return list(set(chain(super().__dir__(), self._elements(), dir(self.internal), self.__extension_methods)))

    def __getattr__(self, item):
        if "_Wrapper__internal" not in self.__dict__:
            raise AttributeError

        if item in dir(self.internal):
            return getattr(self.internal, item)

        if item in self.__extension_methods:
            return partial(self.__find_extension_method(item), self.internal)

        if item in self._elements():
            return self._get(item)

        raise AttributeError

    def __setattr__(self, item, value):
        if "_Wrapper__internal" in self.__dict__ and item in dir(self.internal):
            setattr(self.internal, item, value)

        super().__setattr__(item, value)

    @property
    def internal(self):
        """Access internal Python.NET object."""
        if self.__internal is None:
            raise NotImplementedError

        return self.__internal

    def _elements(self) -> "Iterable[str]":
        """Provide extra elements to be added to ``Wrapper.__dir__``."""
        return []

    def _get(self, _: str) -> Any:
        """Handle extra elements in ``Wrapper.__getattr__``."""
        return None

    @property
    def __extension_methods(self) -> "dict[str, Any]":
        return {x.Name: x for x in TypeManager.Instance.GetExtensionMethods(self.internal.GetType())}

    def __find_extension_method(self, name: str) -> "Optional[Any]":
        try:
            full_name = self.__extension_methods[name].DeclaringType.FullName
            mod_name, _, class_name = full_name.rpartition(".")
            return getattr(getattr(import_module(mod_name), class_name), name)
        except KeyError as e:
            raise AttributeError from e

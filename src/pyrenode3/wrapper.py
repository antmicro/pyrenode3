from collections import defaultdict
from functools import partial
from importlib import import_module
from itertools import chain
from typing import Any, Iterable, Optional

from Antmicro.Renode.Utilities import TypeManager


class MethodDispatcher:
    def __init__(self, callables) -> None:
        self._callables = callables
        if not self._callables or not all([callable(x) for x in callables]):
            msg = "Method dispatcher requires an iterator over callables."
            raise ValueError(msg)

    def __call__(self, *args, **kwargs):
        exceptions = []
        for callable in self._callables:
            try:
                return callable(*args, **kwargs)
            except TypeError as e:
                exceptions.append(e)
                continue

        raise RuntimeError(exceptions)

    def __repr__(self):
        return f"{self.__class__.__name__}([{', '.join(map(repr, self._callables))}])"


class Wrapper:
    """A class used for providing Python.NET objects with extension methods and helpers."""

    def __init__(self, internal=None):
        self.__internal = internal

    def __dir__(self) -> "Iterable[str]":
        return list(set(chain(super().__dir__(), self._elements(), dir(self.internal), self._get_extension_methods())))

    def __getattr__(self, item):
        if "_Wrapper__internal" not in self.__dict__:
            raise AttributeError

        callables = []

        if item in dir(self.internal):
            internal_attr = getattr(self.internal, item)
            if not callable(internal_attr):
                return internal_attr

            callables.append(internal_attr)

        if item in self._get_extension_methods():
            extension_method = partial(self._find_extension_method(item), self.internal)
            callables.append(extension_method)

        if len(callables) == 1:
            return callables[0]
        elif len(callables) > 1:
            return MethodDispatcher(callables)

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

    def _get_extension_methods(self) -> "dict[str, Any]":
        methods = defaultdict(set)
        for method in TypeManager.Instance.GetExtensionMethods(self.internal.GetType()):
            dtype = method.DeclaringType
            parent = dtype.Namespace, dtype.Name
            methods[method.Name].add(parent)

        flattened = dict()
        for method, parents in methods.items():
            if not parents:
                continue

            if len(parents) > 1:
                # msg = f"Multiple classes define '{method}' extension method: {parents}"
                # raise RuntimeError(msg) # warning should be added there
                continue

            flattened[method] = next(iter(parents))

        return flattened

    def _find_extension_method(self, name: str) -> "Optional[Any]":
        try:
            mod_name, class_name = self._get_extension_methods()[name]
            return getattr(getattr(import_module(mod_name), class_name), name)
        except KeyError as e:
            raise AttributeError from e

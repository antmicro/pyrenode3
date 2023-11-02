try:
    import bpython
except ModuleNotFoundError as e:
    raise ImportError from e

import pyrenode3


def main():
    local = {
        "e": pyrenode3.wrappers.Emulation(),
        "m": pyrenode3.wrappers.Monitor(),
        "RPath": pyrenode3.RPath,
        "interface_to_class": pyrenode3.interface_to_class,
    }

    for wrapper_name in pyrenode3.wrappers.__all__:
        local[wrapper_name] = getattr(pyrenode3.wrappers, wrapper_name)

    bpython.embed(local)

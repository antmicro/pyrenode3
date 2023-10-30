import logging

import pyrenode3

if __name__ == "__main__":
    local = {
        "e": pyrenode3.wrappers.Emulation(),
        "m": pyrenode3.wrappers.Monitor(),
        "RPath": pyrenode3.RPath,
        "interface_to_class": pyrenode3.interface_to_class,
    }

    for wrapper_name in pyrenode3.wrappers.__all__:
        local[wrapper_name] = getattr(pyrenode3.wrappers, wrapper_name)

    try:
        import bpython

        bpython.embed(local)
    except ModuleNotFoundError:
        logging.critical("bpython is required for the interactive mode.")

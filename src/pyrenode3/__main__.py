import logging

from pyrenode3.wrappers import Emulation

if __name__ == "__main__":
    local = {
        "Emulation": Emulation,
    }

    try:
        import bpython

        bpython.embed(local)
    except ModuleNotFoundError:
        logging.critical("bpython is required for the interactive mode.")

from Antmicro.Renode.UserInterface.Commands import ShowBackendAnalyzerCommand

from pyrenode3 import wrappers
from pyrenode3.inits import XwtInit
from pyrenode3.wrapper import Wrapper


class Analyzer(Wrapper):
    def __init__(self, peripheral: "wrappers.Peripheral"):
        XwtInit()
        monitor = wrappers.Monitor()
        monitor.Machine = peripheral.mach.internal
        analyzer = ShowBackendAnalyzerCommand(monitor.internal).GetAnalyzer(peripheral.path, None)
        super().__init__(analyzer)

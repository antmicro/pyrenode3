from Antmicro.Renode.UserInterface.Commands import ShowBackendAnalyzerCommand

from pyrenode3 import wrappers
from pyrenode3.inits import XwtInit
from pyrenode3.wrapper import Wrapper


class Analyzer(Wrapper):
    def __init__(self, peripheral: "wrappers.Peripheral"):
        XwtInit()
        analyzer = ShowBackendAnalyzerCommand.GetAnalyzer(peripheral.internal, None)
        super().__init__(analyzer)

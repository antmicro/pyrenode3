from Antmicro.Renode import Testing
from System import String

from pyrenode3 import wrappers
from pyrenode3.wrapper import Wrapper


class LEDTester(Wrapper):
    def __init__(self, emulation: "wrappers.Emulation", peripheral: "wrappers.Peripheral", name: str, defaultTimeout: float = 0):
        self.__led_tester = Testing.LEDTester(peripheral.internal, (defaultTimeout))
        super().__init__(self.__led_tester)

        emulation.ExternalsManager.AddExternal(self.__led_tester, String(name))
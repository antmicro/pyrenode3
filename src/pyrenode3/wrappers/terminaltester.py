from Antmicro.Renode import Testing
from Antmicro.Renode.Time import TimeInterval

from pyrenode3 import wrappers
from pyrenode3.wrapper import Wrapper


class TerminalTester(Wrapper):
    def __init__(self, peripheral: "wrappers.Peripheral", timeout: float, *args, **kwargs):
        self.__term_tester = Testing.TerminalTester(self.to_interval(timeout), *args, **kwargs)
        super().__init__(self.__term_tester)

        self.__term_tester.AttachTo(peripheral.internal)

    @classmethod
    def to_interval(cls, time: float):
        return TimeInterval.FromMicroseconds(int(time * 1e6))

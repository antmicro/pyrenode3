import atexit
import time
from threading import Thread

from Antmicro.Renode import Emulator
from Antmicro.Renode.Analyzers import LoggingUartAnalyzer
from Antmicro.Renode.Backends.Video import VideoBackend
from Antmicro.Renode.Core import EmulationManager
from Antmicro.Renode.Extensions.Analyzers.Video import DummyVideoAnalyzer, VideoAnalyzer
from Antmicro.Renode.Peripherals.UART import UARTBackend
from Antmicro.Renode.UI import (
    ConsoleWindowBackendAnalyzer,
    WindowedUserInterfaceProvider,
    XwtProvider,
)

from pyrenode3.singleton import MetaSingleton


class Cleaner(metaclass=MetaSingleton):
    """A helper class used for cleaning up on exit in a specified order."""

    def __init__(self):
        self.__to_clean = {}
        atexit.register(self.__clean)

    def add(self, pos, clean_func):
        """Add a clean-up function.

        Parameters
        ----------
        pos : int
            position (lower first)

        clean_func
            clean-up function
        """
        self.__to_clean[pos] = clean_func

    def add_multiple(self, *args):
        for pos, c in args:
            self.add(pos, c)

    def __clean(self):
        for _, c in sorted(self.__to_clean.items(), key=lambda x: x[0]):
            c()


class EmulatorInit(metaclass=MetaSingleton):
    """A class used for initializing the emulator."""

    def __init__(self):
        EmulationManager.RebuildInstance()

        Emulator.ShowAnalyzers = True

        Emulator.BeforeExit += Emulator.DisposeAll

        self.__thread = Thread(target=Emulator.ExecuteAsMainThread, daemon=True)
        self.__thread.start()

        Cleaner().add_multiple(
            (0, EmulationManager.Instance.Clear),
            (10, Emulator.FinishExecutionAsMainThread),
        )


class XwtInit(metaclass=MetaSingleton):
    """A class used for initializing XWT."""

    def __init__(self):
        EmulatorInit()

        self.provider = None

        self.__initialize()

    def __initialize(self):
        self.provider = XwtProvider.Create(WindowedUserInterfaceProvider())

        self.__set_preferred_analyzer()

        if self.provider is None:
            return False

        Cleaner().add(3, self.__cleanup)

        return True

    def __cleanup(self):
        if self.provider is None:
            return

        self.provider.Dispose()

        while self.provider.UiThreadId != -1:
            time.sleep(0.1)

    def __set_preferred_analyzer(self):
        if self.provider is not None:
            uart_analyzer_type = ConsoleWindowBackendAnalyzer
            video_analyzer_type = VideoAnalyzer
        else:
            uart_analyzer_type = LoggingUartAnalyzer
            video_analyzer_type = DummyVideoAnalyzer

        def set_analyzers():
            EmulationManager.Instance.CurrentEmulation.BackendManager.SetPreferredAnalyzer(
                UARTBackend, uart_analyzer_type
            )
            EmulationManager.Instance.CurrentEmulation.BackendManager.SetPreferredAnalyzer(
                VideoBackend, video_analyzer_type
            )

        set_analyzers()
        EmulationManager.Instance.EmulationChanged += set_analyzers

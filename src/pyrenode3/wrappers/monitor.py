from Antmicro.Renode import UserInterface
from Antmicro.Renode.Core import ObjectCreator

from pyrenode3 import RenodeLoader
from pyrenode3.conversion import interface_to_class
from pyrenode3.inits import EmulatorInit
from pyrenode3.singleton import MetaSingleton
from pyrenode3.wrapper import Wrapper


class Monitor(Wrapper, metaclass=MetaSingleton):
    """Wrapper of ``Monitor``."""

    def __init__(self):
        with RenodeLoader().in_root():
            EmulatorInit()

            context = ObjectCreator.Instance.OpenContext()
            monitor = UserInterface.Monitor()
            context.RegisterSurrogate(UserInterface.Monitor, monitor)
            monitor.Interaction = UserInterface.CommandInteractionEater()

        super().__init__()

    @property
    def internal(self):
        return ObjectCreator.Instance.GetSurrogate(UserInterface.Monitor)

    @property
    def interaction(self):
        return interface_to_class(self.internal.Interaction)

    def execute(self, command: str) -> (str, str):
        """Execute monitor command.

        Parameters
        ----------
            command: str
                command to execute

        Returns
        -------
            str
                monitor's output
        """
        ci = UserInterface.CommandInteractionEater()
        with RenodeLoader().in_root():
            self.HandleCommand(command, ci)

        return ci.GetContents(), ci.GetError()

    def execute_script(self, path: str) -> (str, str):
        self.interaction.Clear()
        with RenodeLoader().in_root():
            self.TryExecuteScript(path)

        return self.interaction.GetContents(), self.interaction.GetError()

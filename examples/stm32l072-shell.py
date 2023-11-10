#!/usr/bin/env -S python3 -m bpython -i

from pyrenode3.wrappers import Analyzer, Emulation, Monitor

e = Emulation()
m = Monitor()

stm32l072 = e.add_mach("stm32l072")
stm32l072.load_repl("platforms/cpus/stm32l072.repl")

stm32l072.load_elf(
    "https://dl.antmicro.com/projects/renode/stm32l07--zephyr-shell_module.elf-s_1195760-e9474da710aca88c89c7bddd362f7adb4b0c4b70"
)

Analyzer(stm32l072.sysbus.usart2).Show()

e.StartAll()

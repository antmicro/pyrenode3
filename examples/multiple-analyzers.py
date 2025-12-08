# Additionall packages
# pip install requests git+https://github.com/antmicro/dts2repl.git git+https://github.com/antmicro/pyrenode3.git

import requests
import time

from dts2repl import dts2repl
from pathlib import Path
from pyrenode3.wrappers import Analyzer, Emulation, Peripheral
from pyrenode3.inits import XwtInit

from Antmicro.Renode.Peripherals.UART import IUART

dts_url = "https://zephyr-dashboard.renode.io/zephyr/d14a547d4259a541c9baafb4bef6d4e2566f42b7/arduino_nicla_sense_me/hello_world/hello_world.dts"
elf_url = "https://zephyr-dashboard.renode.io/zephyr/d14a547d4259a541c9baafb4bef6d4e2566f42b7/arduino_nicla_sense_me/hello_world/hello_world.elf"

session = requests.Session()

def download(url, dest):
    rsp = session.get(url)
    if rsp.status_code != requests.codes.OK:
        exit(1)

    with open(dest, 'wb') as f:
        f.write(rsp.content)

def create_repl(dts, dest):
    repl = dts2repl.generate(dts)
    if repl == "":
        exit(1)

    with open(dest, "w") as f:
        f.write(repl)

def get_all_uarts(machine):
    uarts = list(machine.GetPeripheralsOfType[IUART]())
    return [(u, Peripheral(u).name) for u in uarts]

displayed_uarts = set()
def create_callback(uart, uart_name):
    def func(char):
        print(chr(char), end="")
        if uart_name not in displayed_uarts:
            print(f"display {uart_name} ({id(uart)})")
            Analyzer(Peripheral(uart)).Show()
            displayed_uarts.add(uart_name)
    return func

def setup_machine(machine_name):
    machine1 = emu.add_mach(machine_name)
    machine1.load_repl(str(Path("example.repl").resolve()))
    machine1.load_elf(str("example.elf"))

    all_uarts = get_all_uarts(machine1)
    if len(all_uarts) > 0:
        for uart, uart_name in all_uarts:
            uart.CharReceived += create_callback(uart, f"{machine_name}_{uart_name}")

download(dts_url, "example.dts")
download(elf_url, "example.elf")
create_repl("example.dts", "example.repl")

emu = Emulation()

# XXX: We must invoke XwtInit() here, because initializing it from a callback registered as
#      CharReceived is not safe (Analyzer() calls it when it is not initialized yet). The same
#      requirement stands for all singleton classes defined in pyrenode3.
XwtInit()

setup_machine("machine1")
setup_machine("machine2")

emu.StartAll()

time.sleep(5)

#!/usr/bin/env -S python3 -m bpython -i

from pyrenode3 import RPath
from pyrenode3.wrappers import Analyzer, Emulation, Monitor, TerminalTester

from Antmicro.Renode.Peripherals.CPU import RegisterValue

e = Emulation()
m = Monitor()
e.CreateUSBConnector("usb_connector")

fomu = e.add_mach("fomu")
fomu.load_repl("platforms/cpus/fomu.repl")
fomu.load_elf(
    "https://dl.antmicro.com/projects/renode/fomu--foboot.elf-s_112080-c31fe1f32fba7894338f3cf4bfb82ec2a8265683"
)
e.Connector.Connect(fomu.sysbus.valenty.internal, e.externals.usb_connector)

hifive = e.add_mach("hifive")
hifive.load_repl("platforms/cpus/sifive-fu540.repl")
hifive.load_elf(
    "https://dl.antmicro.com/projects/renode/hifive-unleashed--bbl.elf-s_17219640-c7e1b920bf81be4062f467d9ecf689dbf7f29c7a"
)

hifive.sysbus.LoadFdt(
    RPath(
        "https://dl.antmicro.com/projects/renode/hifive-unleashed--devicetree.dtb-s_10532-70cd4fc9f3b4df929eba6e6f22d02e6ce4c17bd1"
    ).path,
    0x81000000,
    "earlyconsole mem=256M@0x80000000",
)

hifive.sysbus.LoadSymbolsFrom(
    RPath(
        "https://dl.antmicro.com/projects/renode/hifive-unleashed--vmlinux.elf-s_80421976-46788813c50dc7eb1a1a33c1730ca633616f75f5"
    ).read_file_path
)

hifive.sysbus.e51.SetRegisterUnsafe(11, RegisterValue.Create(0x81000000, 64))
hifive.LoadPlatformDescriptionFromString("usb: USB.MPFS_USB @ sysbus 0x30020000 { MainIRQ -> plic@0x20 }")


Analyzer(hifive.sysbus.uart0).Show()

t = TerminalTester(hifive.sysbus.uart0, 60)
t.WaitFor(["buildroot login:"], includeUnfinishedLine=True)
t.WriteLine("root")
t.WaitFor(["Password:"], includeUnfinishedLine=True)
t.WriteLine("root")

e.externals.usb_connector.RegisterInController(e.hifive.sysbus.usb.internal)

# pyrenode3

Copyright (c) 2023 Antmicro

A Python library for interacting with Renode programmatically.

## Installation

Use pip to install pyrenode3:
```
pip install 'pyrenode3[all] @ git+https://github.com/antmicro/pyrenode3.git'
```

then download Renode Arch package from [here](https://builds.renode.io/renode-latest.pkg.tar.xz) and set `PYRENODE_ARCH_PKG` to package's location.

## Running a demo

To quickly run a sample demo, install the package and run:

```
wget https://builds.renode.io/renode-latest.pkg.tar.xz
wget https://raw.githubusercontent.com/antmicro/pyrenode3/main/examples/unleashed-fomu.py
export PYRENODE_ARCH_PKG=`pwd`/renode-latest.pkg.tar.xz

bpython -i unleashed-fomu.py
```

This will spawn a two-machine demo scenario and, when the Linux boots to shell, you will be able to interact with the simulation via bpython interface.


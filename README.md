# pyrenode3

Copyright (c) 2023 Antmicro

A Python library for interacting with Renode programmatically.

## Installation

Use pip to install pyrenode3:
```
pip install 'pyrenode3[all] @ git+https://github.com/antmicro/pyrenode3.git'
```

then download Renode Arch package from [here](https://builds.renode.io/renode-latest.pkg.tar.xz) and set `PYRENODE_PKG` to package's location.

## Running a demo

To quickly run a sample demo, install the package and run:

```
wget https://builds.renode.io/renode-latest.pkg.tar.xz
wget https://raw.githubusercontent.com/antmicro/pyrenode3/main/examples/unleashed-fomu.py
export PYRENODE_PKG=`pwd`/renode-latest.pkg.tar.xz

bpython -i unleashed-fomu.py
```

This will spawn a two-machine demo scenario and, when the Linux boots to shell, you will be able to interact with the simulation via bpython interface.

## Using pyrenode3 with different Renode configurations

`pyrenode3` can be configured using environment variables:

- `PYRENODE_PKG` - Specifies the location of Renode package that will be used by `pyrenode3`.
- `PYRENODE_BUILD_DIR` - Specifies the location of Renode source directory.
    `pyrenode3` will use Renode which was built in that directory.
    To modify the output directory used as a source of Renode binaries (location of `Renode.exe`), you must set the `PYRENODE_BUILD_OUTPUT` variable, with a path relative to `PYRENODE_BUILD_DIR`.
- `PYRENODE_RUNTIME` -- Specifies runtime which is used to run Renode.
    Supported runtimes: `mono` (default), `dotnet` (.NET).
- `PYRENODE_BIN` -- Specifies the location of Renode portable binary that will be used by `pyrenode3`.

`PYRENODE_PKG` and `PYRENODE_BUILD_DIR` are mutually exclusive.
Exactly one of them must be specified to use `pyrenode3` successfully.

### Supported configurations

|                    | Mono               | .NET               |
| :----------------- | :----------------: | :----------------: |
| Package            | :white_check_mark: | :x:                |
| Built from sources | :white_check_mark: | :white_check_mark: |
| Portable binary    | :x:                | :white_check_mark: |

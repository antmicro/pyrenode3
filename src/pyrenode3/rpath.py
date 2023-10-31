from pathlib import Path
from typing import Union
from urllib.parse import urlparse

from Antmicro.Renode.Utilities import ReadFilePath
from System import Uri

from pyrenode3 import wrappers
from pyrenode3.loader import RenodeLoader


class RPath:
    """A class used for fetching files and converting paths."""

    def __init__(self, location: "Union[str, Path]"):
        self.__result = self.__fetch(location)

    @property
    def path(self) -> str:
        return str(self.__result)

    @property
    def read_file_path(self) -> "ReadFilePath":
        return ReadFilePath(str(self.__result))

    @classmethod
    def in_root(cls):
        return RenodeLoader().in_root()

    @classmethod
    def __fetch_http(cls, uri: str):
        fetcher = wrappers.Emulation().FileFetcher
        res, filename = fetcher.TryFetchFromUri(Uri(uri))
        if not res:
            msg = f"Downloading from '{uri}' failed."
            raise FileNotFoundError(msg)

        return Path(filename)

    @classmethod
    def __fetch_local(cls, path: "Union[str, Path]"):
        res = Path(path)
        if not res.exists():
            msg = f"'{path}' doesn't exist."
            raise FileNotFoundError(msg)

        return res

    def __fetch(self, location: "Union[str, Path]") -> "Path":
        if isinstance(location, Path):
            return self.__fetch_local(location)

        scheme = urlparse(location).scheme
        if scheme in ["http", "https"]:
            return self.__fetch_http(location)

        return self.__fetch_local(location)

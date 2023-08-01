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
        self.__location = location

    @property
    def path(self) -> str:
        return str(self.__fetch())

    @property
    def read_file_path(self) -> "ReadFilePath":
        return ReadFilePath(str(self.__fetch()))

    @classmethod
    def in_root(cls):
        return RenodeLoader().in_root()

    def __fetch(self):
        if isinstance(self.__location, Path):
            return self.__fetch_local()

        scheme = urlparse(self.__location).scheme
        if scheme in ["http", "https"]:
            return self.__fetch_http()

        return self.__fetch_local()

    def __fetch_http(self):
        fetcher = wrappers.Emulation().FileFetcher
        res, filename = fetcher.TryFetchFromUri(Uri(self.__location))
        if not res:
            msg = f"Downloading from '{self.__location}' failed."
            raise ValueError(msg)

        return Path(filename)

    def __fetch_local(self):
        res = Path(self.__location)
        if not res.exists():
            msg = f"'{self.__location}' doesn't exist."
            raise ValueError(msg)

        return res

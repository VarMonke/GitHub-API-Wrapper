__all__ = ("File",)

import os
from io import BytesIO, StringIO
from pathlib import Path
from typing import Union


class File:
    def __init__(self, file: Union[str, StringIO, BytesIO], /, *, filename: str) -> None:
        self._file = file
        self.name = filename

    def read(self) -> str:
        f = self._file

        if isinstance(f, BytesIO):
            return f.read().decode("utf-8")

        if isinstance(f, StringIO):
            return f.getvalue()

        if os.path.exists(f):
            return Path(f).read_text()

        return f

from pathlib import Path
import os
from typing import Union
from io import BytesIO, StringIO

__all__ = ("File",)


class File:
    def __init__(self, file: Union[str, StringIO, BytesIO], /, *, filename: str) -> None:
        self.file = file
        self.name = filename

    def read(self) -> str:
        if isinstance(self.file, BytesIO):
            return self.file.read().decode("utf-8")

        if isinstance(self.file, StringIO):
            return self.file.getvalue()

        if os.path.exists(self.file):
            return Path(self.file).read_text()

        return self.file

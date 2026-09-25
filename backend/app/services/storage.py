import os
import uuid
from pathlib import Path
from typing import BinaryIO


class StorageError(Exception):
    pass


class FileTooLarge(StorageError):
    pass


class LocalStorage:
    def __init__(self, root: Path | None = None):
        default_root = Path(__file__).resolve().parents[3] / "storage"
        self.root = (root or Path(os.getenv("STORAGE_ROOT", default_root))).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root != path and self.root not in path.parents:
            raise StorageError("Invalid storage key")
        return path

    def save(self, source: BinaryIO, edition_id: uuid.UUID, max_bytes: int) -> tuple[str, int]:
        key = f"books/{edition_id}/{uuid.uuid4().hex}.pdf"
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        try:
            with path.open("wb") as target:
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise FileTooLarge
                    target.write(chunk)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return key, size

    def open(self, key: str, mode: str = "rb"):
        return self._path(key).open(mode)

    def path(self, key: str) -> Path:
        path = self._path(key)
        if not path.is_file():
            raise StorageError("Stored file is missing")
        return path

    def delete(self, key: str) -> None:
        path = self._path(key)
        path.unlink(missing_ok=True)
        try:
            path.parent.rmdir()
        except OSError:
            pass

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()


storage = LocalStorage()

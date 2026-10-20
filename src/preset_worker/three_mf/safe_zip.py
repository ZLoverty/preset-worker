from __future__ import annotations

import hashlib
import io
import posixpath
import zipfile
from dataclasses import dataclass


class SafeZipError(ValueError):
    pass


@dataclass(frozen=True)
class ZipLimits:
    max_compressed_size: int = 256 * 1024 * 1024
    max_total_uncompressed_size: int = 1024 * 1024 * 1024
    max_entry_count: int = 10_000
    max_entry_size: int = 256 * 1024 * 1024
    max_compression_ratio: float = 100.0


def _safe_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    if not normalized or normalized.startswith("/") or "\x00" in normalized:
        raise SafeZipError("unsafe archive path")
    if posixpath.normpath(normalized) != normalized or normalized == ".." or normalized.startswith("../"):
        raise SafeZipError("archive path traversal")
    return normalized


class SafeZipReader:
    def __init__(self, data: bytes, limits: ZipLimits | None = None):
        self.data = data
        self.limits = limits or ZipLimits()
        if len(data) > self.limits.max_compressed_size:
            raise SafeZipError("compressed archive exceeds limit")
        try:
            self.archive = zipfile.ZipFile(io.BytesIO(data))
            infos = self.archive.infolist()
        except (OSError, zipfile.BadZipFile) as exc:
            raise SafeZipError("invalid ZIP archive") from exc
        if len(infos) > self.limits.max_entry_count:
            raise SafeZipError("archive entry count exceeds limit")
        self._infos: dict[str, zipfile.ZipInfo] = {}
        total = 0
        for info in infos:
            name = _safe_name(info.filename)
            if name in self._infos:
                raise SafeZipError("duplicate normalized archive path")
            if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA):
                raise SafeZipError(f"unsupported compression method: {info.compress_type}")
            if info.file_size > self.limits.max_entry_size:
                raise SafeZipError("archive entry exceeds limit")
            if info.compress_size and info.file_size / info.compress_size > self.limits.max_compression_ratio:
                raise SafeZipError("archive compression ratio exceeds limit")
            total += info.file_size
            if total > self.limits.max_total_uncompressed_size:
                raise SafeZipError("total uncompressed size exceeds limit")
            self._infos[name] = info

    @property
    def names(self) -> list[str]:
        return list(self._infos)

    def read(self, name: str, *, max_bytes: int | None = None) -> bytes:
        normalized = _safe_name(name)
        info = self._infos.get(normalized)
        if info is None:
            raise KeyError(normalized)
        limit = min(info.file_size, max_bytes or info.file_size)
        with self.archive.open(info, "r") as stream:
            value = stream.read(limit + 1)
        if len(value) > limit:
            raise SafeZipError("decompressed entry exceeds read limit")
        return value

    def close(self) -> None:
        self.archive.close()

    def __enter__(self) -> "SafeZipReader":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def archive_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

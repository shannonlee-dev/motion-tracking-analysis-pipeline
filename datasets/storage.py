"""Pinned downloads, safe extraction and atomic writes shared by preparation."""

import hashlib
import json
import os
import shutil
import ssl
import stat
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(path: Path, record: dict) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing input: {path}")
    if (
        record.get("bytes") is not None and path.stat().st_size != record["bytes"]
    ) or sha256(path) != record["sha256"]:
        raise ValueError(
            f"Checksum mismatch: {path}. Restore the pinned source; existing files were not overwritten."
        )


def write_json(path: Path, value: object) -> None:
    content = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    if path.is_file() and path.read_bytes() == content:
        return
    atomic_bytes(path, content)


def atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def download_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    # python.org macOS installs can have no CA bundle until their certificate
    # installer is run. Use the OS bundle, preserving explicit trust settings.
    if (
        sys.platform == "darwin"
        and "SSL_CERT_FILE" not in os.environ
        and "SSL_CERT_DIR" not in os.environ
        and not context.cert_store_stats()["x509_ca"]
        and Path("/etc/ssl/cert.pem").is_file()
    ):
        context.load_verify_locations(cafile="/etc/ssl/cert.pem")
    return context


def download(path: Path, url: str, record: dict, *, offline: bool = False) -> Path:
    if path.exists():
        verify(path, record)
        return path
    if offline:
        raise FileNotFoundError(f"Missing cached source in offline mode: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        print(f"Downloading {path.name}", flush=True)
        with (
            urllib.request.urlopen(
                url, timeout=120, context=download_ssl_context()
            ) as response,
            temporary.open("wb") as stream,
        ):
            shutil.copyfileobj(response, stream)
        verify(temporary, record)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def safe_path(root: Path, name: str) -> Path:
    # Also reject Windows separators when extracting on Unix.
    name = name.replace("\\", "/")
    path = root / name
    if ":" in name or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Unsafe archive path: {name}")
    return path


def extract(archive: Path, destination: Path) -> None:
    """Verify cached extracted bytes; replace only missing/damaged archive members."""
    destination.mkdir(parents=True, exist_ok=True)
    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                path = safe_path(destination, member.filename)
                if stat.S_ISLNK(member.external_attr >> 16):
                    raise ValueError("Archive symlinks are not supported")
                if not member.is_dir():
                    content = source.read(member)  # checks ZIP CRC
                    if not path.exists() or path.read_bytes() != content:
                        atomic_bytes(path, content)
    else:
        import libarchive

        with libarchive.file_reader(str(archive)) as source:
            for member in source:
                path = safe_path(destination, member.pathname)
                if member.isdir:
                    continue
                if not member.isfile:
                    raise ValueError("Unexpected archive entry type")
                content = b"".join(member.get_blocks())
                if not path.exists() or path.read_bytes() != content:
                    atomic_bytes(path, content)

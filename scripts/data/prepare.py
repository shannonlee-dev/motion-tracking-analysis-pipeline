"""Prepare official public benchmarks; verify pinned source checksums."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

from scripts.common import ROOT


def verify(content, record):
    if len(content) != record['bytes'] or hashlib.sha256(content).hexdigest() != record['sha256']:
        raise ValueError(f"Source checksum mismatch: {record['file']}")


def download(url, limit=None):
    req = urllib.request.Request(url, headers={'Range': f'bytes=0-{limit-1}'} if limit else {})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read(limit) if limit else response.read()


def safe_path(root, name):
    path = Path(name)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Unsafe archive path')
    return root/path


def main():
    # ALOI archives are read as data only; selected original files are hash checked.
    records = json.loads((ROOT/'data/aloi/sources.json').read_text())
    cache = {}
    dest = ROOT/'data/aloi/raw'
    dest.mkdir(parents=True, exist_ok=True)
    for rec in records:
        path = dest/rec['file']
        if path.exists():
            verify(path.read_bytes(), rec)
            continue
        url = rec['archive_url']
        if url not in cache:
            # Official uncompressed mask TAR starts with object 1. The selected member
            # is wholly within this prefix; its own pinned checksum is verified below.
            cache[url] = download(url, 524288 if url.endswith('aloi_mask.tar') else None)
        with tarfile.open(fileobj=io.BytesIO(cache[url])) as archive:
            content = archive.extractfile(rec['archive_member']).read()
        verify(content, rec)
        path.write_bytes(content)

    import libarchive  # optional preparation dependency; also needs OS libarchive
    for rec in json.loads((ROOT/'data/lasiesta/sources.json').read_text()):
        path = ROOT/'data/lasiesta'/rec['file']
        if not path.exists():
            content = download(rec['url'])
            verify(content, rec)
            path.write_bytes(content)
        verify(path.read_bytes(), rec)
        with libarchive.file_reader(str(path)) as archive:
            for entry in archive:
                out = safe_path(ROOT/'data/lasiesta/extracted', entry.pathname)
                if entry.isdir:
                    out.mkdir(parents=True, exist_ok=True)
                elif entry.isfile:
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with out.open('wb') as handle:
                        for block in entry.get_blocks():
                            handle.write(block)
                else:
                    raise ValueError('Unexpected archive entry type')


if __name__ == '__main__':
    main()

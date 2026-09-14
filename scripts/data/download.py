"""Download public CAVIAR media; record provenance and checksums, never execute it."""
import hashlib
import json
import urllib.request

from scripts.common import ROOT
from scripts.constants import CAVIAR_RAW_DIR, CAVIAR_MANIFEST

DOWNLOAD_TIMEOUT_SECONDS = 90
BASE = 'https://homepages.inf.ed.ac.uk/rbf/'
SOURCES = {
    'meeting.mpg': 'CAVIARDATA1/Meet_WalkSplit/Meet_WalkSplit.mpg',
    'meeting.xml': 'CAVIARDATA1/Meet_WalkSplit/mws1gt.xml',
    'walking.mpg': 'CAVIARDATA1/Walk1/Walk1.mpg',
    'walking.xml': 'CAVIARDATA1/Walk1/wk1gt.xml',
    'stopping.mpg': 'CAVIARDATA2/OneStopNoEnter1cor/OneStopNoEnter1cor.mpg',
    'stopping.xml': 'CAVIARDATA2/OneStopNoEnter1cor/cosne1gt.xml',
}

def main() -> None:
    dest = ROOT / CAVIAR_RAW_DIR
    dest.mkdir(parents=True, exist_ok=True)
    manifest = ROOT/CAVIAR_MANIFEST
    records = {r['file']: r for r in json.loads(manifest.read_text())} if manifest.exists() else {}
    for name, suffix in SOURCES.items():
        path = dest / name
        url = BASE + suffix
        if not path.exists():
            print('Downloading', name, flush=True)
            with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
                content = response.read()
            temp = path.with_suffix('.part')
            temp.write_bytes(content)
            temp.replace(path)
        records[name] = dict(file=name, url=url, bytes=path.stat().st_size,
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    manifest.write_text(json.dumps(list(records.values()), indent=2)+'\n')

if __name__ == '__main__':
    main()

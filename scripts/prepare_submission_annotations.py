"""Rebuild explicit evaluation annotations from local dataset labels."""
import json, hashlib
import xml.etree.ElementTree as E
from pathlib import Path
import cv2, numpy as np

def parse(p, offset=0):
    out = {}
    for f in E.parse(p).getroot().findall('frame'):
        boxes = {}
        for o in f.findall('objectlist/object'):
            b = o.find('box')
            v = {k: float(v) for k, v in b.attrib.items()}
            boxes[o.get('id')] = [v['xc'] - v['w'] / 2, v['yc'] - v['h'] / 2, v['w'], v['h']]
        out[int(f.get('number')) - offset] = boxes
    return out

def main():
    out = Path('results/submission')
    truth = {}
    sources = []
    for n in ['01', '02', '03']:
        p = out / 'annotations' / f'{n}.xml'
        truth[n] = parse(p)
        sources.append(dict(video=n, annotation=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), origin='Cached CAVIAR XML recovered from /tmp/mission-scene-audit; dataset name and visual alignment checked; not prior tracking results'))
    for m in json.load(open('data/reference/manifests/overlap_sources.json')):
        n = Path(m['file']).stem
        p = Path('data/raw/caviar') / m['gt_file']
        truth[n] = {f: b for f, b in parse(p, m['source_start_frame']).items() if 0 <= f < m['frames']}
        sources.append(dict(video=n, annotation=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), source_start=m['source_start_frame']))
    for n, seq in [('15', 'I_OC_01'), ('16', 'I_OC_02'), ('17', 'I_IL_02'), ('18', 'I_IL_01'), ('19', 'I_CA_01')]:
        truth[n] = {}
        for p in sorted(Path('data/raw/lasiesta/' + seq + '-GT').glob('*.png')):
            f = int(p.stem.split('_')[-1]) - 1
            im = cv2.imread(str(p))
            mask = np.all(im == (0, 0, 255), axis=2) | np.all(im == 255, axis=2)
            truth[n][f] = {'1': list(cv2.boundingRect(mask.astype('uint8')))} if mask.any() else {}
        sources.append(dict(video=n, annotation='data/raw/lasiesta/' + seq + '-GT', origin='Red foreground plus white temporarily static object; gray uncertainty ignored; bbox from label mask'))
    anchors = json.loads((out / 'annotations' / '14_anchors.json').read_text())
    truth['14'] = {}
    for group in anchors:
        for (lo, a), (hi, b) in zip(group, group[1:]):
            for f in range(lo, hi + 1):
                truth['14'][f] = {'1': (np.array(a) + (np.array(b) - a) * (f - lo) / (hi - lo)).tolist()}
    sources.append(dict(video='14', origin='Manually observed bbox anchors in 160x120 original frames; interpolated; approximate association labels, not dataset GT', annotation='results/submission/annotations/14_anchors.json'))
    (out / 'ground_truth.json').write_text(json.dumps(truth, separators=(',', ':')) + '\n')
    (out / 'annotation_sources.json').write_text(json.dumps(sources, indent=2) + '\n')
if __name__ == '__main__':
    main()

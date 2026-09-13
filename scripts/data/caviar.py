"""Read CAVIAR frame annotations as top-left bounding boxes."""
import xml.etree.ElementTree as ET


def load_caviar(path):
    result = {}
    for frame in ET.parse(path).getroot().findall('frame'):
        objects = {}
        for obj in frame.findall('./objectlist/object'):
            box = obj.find('box')
            if box is None:
                continue
            xc,yc,w,h = [float(box.get(k)) for k in ('xc','yc','w','h')]
            objects[int(obj.get('id'))] = (xc-w/2,yc-h/2,w,h)
        result[int(frame.get('number'))] = objects
    return result

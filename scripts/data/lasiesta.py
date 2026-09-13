"""LASIESTA frame/annotation pairing and foreground labels."""
import numpy as np


def labels(gt):
    """OpenCV BGR: include temporarily static objects, ignore uncertain pixels."""
    bg = np.all(gt == 0, axis=2)
    uncertain = np.all(gt == 128, axis=2)
    allowed = bg | uncertain
    fg = np.zeros(gt.shape[:2], dtype=bool)
    for color in ((0, 0, 255), (0, 255, 0), (0, 255, 255), (255, 255, 255)):
        fg |= np.all(gt == color, axis=2)
    if not np.all(allowed | fg):
        raise ValueError('Unknown LASIESTA label')
    return fg, ~uncertain


def sequence_paths(root, name):
    images = sorted((root/name).glob(f'{name}-*.bmp'), key=lambda p: int(p.stem.split('-')[-1]))
    truth = sorted((root/(name+'-GT')).glob(f'{name}-GT_*.png'), key=lambda p: int(p.stem.split('_')[-1]))
    if not images or len(images) != len(truth):
        raise ValueError(f'Missing input/GT: {name}')
    for i, (image, gt) in enumerate(zip(images, truth), 1):
        if image.name != f'{name}-{i}.bmp' or gt.name != f'{name}-GT_{i}.png':
            raise ValueError(f'Nonconsecutive input/GT: {name} frame {i}')
    return list(zip(images, truth))

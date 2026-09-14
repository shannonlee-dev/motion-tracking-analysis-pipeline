"""Bounding-box geometry in top-left (x, y, width, height) coordinates."""


BBox = tuple[float, float, float, float]


def intersection_area(a: BBox, b: BBox) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (max(0, min(ax+aw, bx+bw)-max(ax, bx)) *
            max(0, min(ay+ah, by+bh)-max(ay, by)))


def iou(a: BBox, b: BBox) -> float:
    overlap = intersection_area(a, b)
    return overlap/max(a[2]*a[3]+b[2]*b[3]-overlap, 1)

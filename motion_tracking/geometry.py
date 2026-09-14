"""Bounding-box geometry in top-left (x, y, width, height) coordinates."""


def intersection_area(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (max(0, min(ax+aw, bx+bw)-max(ax, bx)) *
            max(0, min(ay+ah, by+bh)-max(ay, by)))


def iou(a, b):
    overlap = intersection_area(a, b)
    return overlap/max(a[2]*a[3]+b[2]*b[3]-overlap, 1)

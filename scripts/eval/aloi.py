"""One real ALOI object: viewpoint, illumination and mask-area occlusion."""
import cv2
import numpy as np
from motion_tracking.vision import TargetMatcher
from motion_tracking.features import (
    FEATURE_COUNT, HOMOGRAPHY_MIN_MATCHES, RANSAC_REPROJECTION_THRESHOLD,
    unique_ratio_matches,
)
from scripts.constants import ALOI_RAW_DIR
from scripts.common import ROOT, RESULTS, write_csv

OCCLUDER_INTENSITY = 127
ALOI_SEED = 0
VIEW_CONDITIONS = ('r0', 'r30', 'r60', 'l1c1', 'l8c1', 'i110', 'i250')
OCCLUSION_FRACTIONS = (0.3, 0.5)
SCENE_PADDING = 80
PANEL_SIZE = (464, 368)
PANEL_COLUMNS = 3


def occlude(image: np.ndarray, mask: np.ndarray, fraction: float) -> tuple[np.ndarray, int]:
    if image.shape[:2] != mask.shape or not 0 <= fraction <= 1 or not mask.any():
        raise ValueError('Invalid mask or fraction')
    # Vertical opaque curtain: include whole preceding columns, then part of one column.
    y, x = np.nonzero(mask)
    order = np.lexsort((y, x))
    count = round(len(x)*fraction)
    covered = np.zeros(mask.shape, dtype=bool)
    if count:
        last = order[count-1]
        yy, xx = np.indices(mask.shape)
        covered = (xx < x[last]) | ((xx == x[last]) & (yy <= y[last]))
    out = image.copy()
    out[covered] = OCCLUDER_INTENSITY
    return out, int(np.count_nonzero(covered & mask))


def main() -> None:
    cv2.setRNGSeed(ALOI_SEED)
    root = ROOT/ALOI_RAW_DIR
    target = cv2.imread(str(root/'1_r0.png'))
    mask = cv2.imread(str(root/'mask.png'), 0)
    if target is None or mask is None:
        raise ValueError('Prepare ALOI originals first')
    mask = mask > 0
    variants = [(name, cv2.imread(str(root/f'1_{name}.png')), 0)
                for name in VIEW_CONDITIONS]
    for fraction in OCCLUSION_FRACTIONS:
        im, pixels = occlude(target, mask, fraction)
        variants.append((f'occlusion{int(fraction*100)}', im, pixels))
    orb = TargetMatcher(target)
    sift = cv2.SIFT_create(nfeatures=FEATURE_COUNT)
    refkp, refdesc = sift.detectAndCompute(target, None)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    rows = []
    panels = []
    for name, im, covered in variants:
        if im is None:
            raise ValueError(name)
        # Equal padding keeps the app's homography area guard valid for a full-frame reference.
        scene = cv2.copyMakeBorder(im, SCENE_PADDING, SCENE_PADDING, SCENE_PADDING, SCENE_PADDING, cv2.BORDER_CONSTANT, value=(0, 0, 0))
        result = orb.match(scene)
        rows.append(dict(condition=name, algorithm='ORB_app', reference_keypoints=len(orb.target_kp),
                         scene_keypoints=result.keypoints, matches=result.matches, inliers=result.inliers,
                         match_rate=result.matches/len(orb.target_kp), found=int(result.found),
                         object_pixels=int(mask.sum()), covered_pixels=covered,
                         occlusion_fraction=covered/int(mask.sum())))
        kp, desc = sift.detectAndCompute(scene, None)
        good = unique_ratio_matches(bf, refdesc, desc)
        inliers = 0
        if len(good) >= HOMOGRAPHY_MIN_MATCHES:
            src = np.float32([refkp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst = np.float32([kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            _, inlier = cv2.findHomography(src, dst, cv2.RANSAC, RANSAC_REPROJECTION_THRESHOLD)
            inliers = int(inlier.sum()) if inlier is not None else 0
        rows.append(dict(condition=name, algorithm='SIFT_reference', reference_keypoints=len(refkp),
                         scene_keypoints=len(kp), matches=len(good), inliers=inliers,
                         match_rate=len(good)/len(refkp), found='', object_pixels=int(mask.sum()),
                         covered_pixels=covered, occlusion_fraction=covered/int(mask.sum())))
        panel = cv2.resize(scene, PANEL_SIZE)
        cv2.putText(panel, f'{name}: ORB {result.matches}/{len(orb.target_kp)} found={result.found}',
                    (8, 22), 0, .45, (0, 255, 255), 1)
        panels.append(panel)
    write_csv(RESULTS/'aloi_features.csv', rows)
    # Keep preview local until source redistribution terms are established.
    cv2.imwrite(str(root/'evaluation.jpg'), np.concatenate(
        [np.concatenate(panels[i:i+PANEL_COLUMNS], axis=1) for i in range(0, len(panels), PANEL_COLUMNS)], axis=0))


if __name__ == '__main__':
    main()

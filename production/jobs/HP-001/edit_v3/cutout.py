# Cut the real products out of the temporal-median plate with GrabCut -> RGBA PNGs (16-bit colour kept as 8-bit sRGB here).
import sys, numpy as np, cv2
med = cv2.imread(sys.argv[1], cv2.IMREAD_UNCHANGED)
img8 = (med.astype(np.float32)/65535*255).clip(0, 255).astype(np.uint8)
OUT = sys.argv[2]
R = {"leather": (778, 1176, 1056, 1532), "ivory": (52, 1168, 316, 1516), "box": (426, 1402, 702, 1586)}
for name, (x0, y0, x1, y1) in R.items():
    pad = 30
    X0, Y0, X1, Y1 = x0-pad, y0-pad, x1+pad, y1+pad
    sub = img8[Y0:Y1, X0:X1].copy()
    mask = np.zeros(sub.shape[:2], np.uint8)
    rect = (pad-8, pad-8, (x1-x0)+16, (y1-y0)+16)
    bgd = np.zeros((1, 65), np.float64); fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(sub, mask, rect, bgd, fgd, 8, cv2.GC_INIT_WITH_RECT)
    m = np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8)
    # keep the largest component, fill holes (carvings), smooth edge
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    k = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]); m = np.where(lab == k, 255, 0).astype(np.uint8)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    hull = np.zeros_like(m); cv2.drawContours(hull, cnts, -1, 255, -1)
    m = cv2.morphologyEx(hull, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.GaussianBlur(m, (0, 0), 1.2)
    sub16 = med[Y0:Y1, X0:X1]
    rgba = np.dstack([sub16, (m.astype(np.uint16)*257)])
    cv2.imwrite(f"{OUT}/cut_{name}.png", rgba)
    prev = sub.copy(); prev[m < 128] = (prev[m < 128]*0.15).astype(np.uint8)
    cv2.imwrite(f"{OUT}/cutprev_{name}.jpg", prev)
    print(name, sub.shape, int((m > 128).mean()*100), "% fg")

import sys, glob, numpy as np, cv2
fs = sorted(glob.glob(sys.argv[1] + "/fr_*.png"))
st = np.stack([cv2.imread(f, cv2.IMREAD_UNCHANGED) for f in fs]).astype(np.float32)
med = np.median(st, axis=0)
cv2.imwrite(sys.argv[2], med.astype(np.uint16))
print(med.shape)

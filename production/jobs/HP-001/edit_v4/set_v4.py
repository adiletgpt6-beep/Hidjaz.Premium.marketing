# Premium product set for the REAL products: wood tabletop in perspective (camera at table height, matching the
# frontal product photo), deep warm background with soft bokeh, a soft "window" light pool, correct shadows.
# The product pixels (cover, ornament, shape) are not altered; only global light/tint matching is applied.
import sys, json, numpy as np, cv2
W, H = 1080, 1920
spec = json.load(open(sys.argv[1])); CUT = sys.argv[2]; OUT = sys.argv[3]

def wood_plane(tex, y_t, light_x):
    t = cv2.imread(tex, cv2.IMREAD_COLOR).astype(np.float32)/255
    t = cv2.rotate(t, cv2.ROTATE_90_CLOCKWISE)                    # grain runs left-right, like a table seen from the front
    t = cv2.resize(t, (2048, 1024), interpolation=cv2.INTER_LANCZOS4)
    th, tw = t.shape[:2]
    src = np.float32([[0, 0], [tw, 0], [tw, th], [0, th]])
    dst = np.float32([[-260, y_t], [W+260, y_t], [W+2600, H+40], [-2600, H+40]])
    plane = cv2.warpPerspective(t, cv2.getPerspectiveTransform(src, dst), (W, H), flags=cv2.INTER_LINEAR)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    depth = np.clip((yy - y_t)/(H - y_t), 0, 1)
    shade = 0.35 + 0.75*np.exp(-((xx - W*(0.5 + 0.28*light_x))/(W*0.55))**2)*np.exp(-((depth - 0.18)/0.35)**2)
    plane *= shade[..., None]*(0.62 + 0.38*(1 - depth))[..., None]
    sheen = np.exp(-((depth - 0.05)/0.05)**2)*0.10                 # soft satin sheen near the far edge
    plane = plane + sheen[..., None]*np.array([0.55, 0.78, 1.0], np.float32)
    return plane, (yy >= y_t)

def backdrop(y_t, light_x, seed, tone):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.array(tone, np.float32)
    g = np.exp(-(((xx - W*(0.5 + 0.25*light_x))/(W*0.7))**2 + ((yy - y_t*0.75)/(H*0.42))**2))
    bg = base[None, None, :]*(0.45 + 1.4*g[..., None])
    rng = np.random.default_rng(seed); bok = np.zeros((H, W), np.float32)
    for _ in range(14):
        cx = rng.uniform(0, W); cy = rng.uniform(H*0.08, y_t*0.92); r = rng.uniform(14, 95)**1.0
        lay = np.zeros((H, W), np.float32); cv2.circle(lay, (int(cx), int(cy)), int(r), float(rng.uniform(0.04, 0.16)), -1, cv2.LINE_AA)
        bok += cv2.GaussianBlur(lay, (0, 0), 6 + r*0.35)
    bok = cv2.GaussianBlur(bok, (0, 0), 4)*(0.4 + 0.9*np.clip(1 - np.abs(xx - W*(0.5 + 0.3*light_x))/W, 0, 1))
    bg = bg + bok[..., None]*np.array([0.35, 0.62, 0.95], np.float32)
    beam = np.exp(-(((xx*0.82 + yy*0.57*(-light_x)) - (W*0.5 - light_x*W*0.15))/(W*0.16))**2)*np.clip(1 - yy/(y_t*1.05), 0, 1)
    bg = bg + cv2.GaussianBlur(beam.astype(np.float32), (0, 0), 30)[..., None]*0.07*np.array([0.6, 0.82, 1.0], np.float32)
    return bg

def load_cut(name):
    a = cv2.imread(f"{CUT}/cut_{name}.png", cv2.IMREAD_UNCHANGED).astype(np.float32)/65535
    ys, xs = np.where(a[..., 3] > 0.5); a = a[ys.min():ys.max()+1, xs.min():xs.max()+1]
    # level the bottom edge (the source shot was slightly turned): small rotation only, design untouched
    al = a[..., 3]; h, w = al.shape; cols = np.arange(int(w*0.1), int(w*0.9))
    bottoms = np.array([np.max(np.where(al[:, c] > 0.5)[0]) for c in cols])
    slope = np.polyfit(cols, bottoms, 1)[0]; ang = float(np.degrees(np.arctan(slope)))
    if abs(ang) > 0.3:
        # vertical shear: straightens the receding bottom/top edges, keeps vertical edges vertical (no lean)
        pad = int(abs(slope)*w) + 4
        M = np.float32([[1, 0, 0], [-slope, 1, pad if slope > 0 else 0]])
        a = cv2.warpAffine(a, M, (w, h + pad), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0, 0))
        ys, xs = np.where(a[..., 3] > 0.5); a = a[ys.min():ys.max()+1, xs.min():xs.max()+1]
    print("  level (shear)", name, round(ang, 2), "deg")
    return np.clip(a[..., :3], 0, 1), np.clip(a[..., 3:4], 0, 1)

for sh in spec:
    y_t = int(H*sh["horizon"]); lx = sh.get("light_from", -1)
    fr = backdrop(y_t, lx, sh.get("seed", 3), sh.get("tone", (0.050, 0.060, 0.115)))
    plane, m = wood_plane(sh["wood"], y_t, lx)
    fr = np.where(m[..., None], plane, fr)
    edge = np.exp(-((np.arange(H, dtype=np.float32) - y_t)/2.5)**2)[:, None, None]*0.05
    fr = np.clip(fr + edge, 0, 1)
    for it in sh["items"]:
        rgb, al = load_cut(it["src"]); h0, w0 = rgb.shape[:2]; k = it["width"]/w0
        rgb = cv2.resize(rgb, (int(w0*k), int(h0*k)), interpolation=cv2.INTER_LANCZOS4)
        al = cv2.resize(al, (int(w0*k), int(h0*k)), interpolation=cv2.INTER_LINEAR)[..., None]
        bl = cv2.GaussianBlur(rgb, (0, 0), 1.2); rgb = np.clip(rgb + 0.4*(rgb - bl), 0, 1)
        h, w = rgb.shape[:2]; cx = int(W*it["x"]); base = int(H*it["base"]); x0 = cx - w//2; y0 = base - h
        gx = np.linspace(-1, 1, w, dtype=np.float32)[None, :, None]; gy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        rgb = np.clip(rgb*it.get("exposure", 0.97)*(1 + 0.14*(-lx)*gx)*(1.04 - 0.12*gy)*np.array([0.97, 1.0, 1.03], np.float32), 0, 1)
        shm = np.zeros((H, W), np.float32)
        d = int(-lx*h*0.42)
        poly = np.array([[x0+6, base], [x0+w-6, base], [x0+w-6+d, base-int(h*0.07)], [x0+6+d, base-int(h*0.07)]], np.int32)
        cv2.fillConvexPoly(shm, poly, it.get("cast", 0.45)); shm = cv2.GaussianBlur(shm, (0, 0), 16)
        ct = np.zeros((H, W), np.float32); cv2.ellipse(ct, (cx, base-2), (int(w*0.51), 7), 0, 0, 360, 0.8, -1)
        ct = cv2.GaussianBlur(ct, (0, 0), 5)
        fr *= (1 - np.clip(shm + ct, 0, 0.88)[..., None])
        ys0, xs0 = max(y0, 0), max(x0, 0); ys1, xs1 = min(y0+h, H), min(x0+w, W)
        mm = al[ys0-y0:ys1-y0, xs0-x0:xs1-x0]
        fr[ys0:ys1, xs0:xs1] = fr[ys0:ys1, xs0:xs1]*(1-mm) + rgb[ys0-y0:ys1-y0, xs0-x0:xs1-x0]*mm
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    fr *= np.clip(1.12 - 0.7*(((xx-W/2)/(W*0.8))**2 + ((yy-H*0.5)/(H*0.75))**2), 0.35, 1)[..., None]
    g = cv2.resize(np.random.default_rng(1).normal(0, 1, (H//2, W//2)).astype(np.float32), (W, H))[..., None]
    fr = np.clip(fr + g*0.007, 0, 1)
    cv2.imwrite(f"{OUT}/{sh['id']}.png", (fr*255+0.5).astype(np.uint8)); print("set", sh["id"])

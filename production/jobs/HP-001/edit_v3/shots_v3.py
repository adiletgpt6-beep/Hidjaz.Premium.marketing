# V3 shot renderer: (a) studio packshots of the REAL products (GrabCut cutouts from the source plate) on a clean
# synthetic studio set — one composition, nothing behind it; (b) full-frame stills (locally generated scenes) with a
# very slow camera move. No particles, no light sweeps, no translucent overlays.
import sys, json, subprocess, numpy as np, cv2
W, H, FPS = 1080, 1920, 30
spec = json.load(open(sys.argv[1])); OUT = sys.argv[2]; CUT = sys.argv[3]
only = sys.argv[4].split(",") if len(sys.argv) > 4 else None
def smooth(t): return t*t*(3-2*t)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

def load_cut(name):
    a = cv2.imread(f"{CUT}/cut_{name}.png", cv2.IMREAD_UNCHANGED).astype(np.float32)/65535
    ys, xs = np.where(a[..., 3] > 0.5); a = a[ys.min():ys.max()+1, xs.min():xs.max()+1]   # tight to the product
    rgb, al = a[..., :3], a[..., 3:4]
    hh = rgb.shape[0]; rgb = rgb*np.linspace(1.06, 0.86, hh, dtype=np.float32)[:, None, None]   # soft key light from above
    rgb = np.clip(rgb, 0, 1); rgb = rgb*rgb*(3-2*rgb)*0.25 + rgb*0.75      # gentle contrast
    return rgb, al

def studio_set(tone=(0.075, 0.045, 0.11), floor_y=0.66):
    # BGR studio: deep burgundy-brown backdrop, soft key-light cone from above, a slightly lighter floor plane
    base = np.array(tone, np.float32)
    g = np.exp(-(((xx - W*0.5)/(W*0.55))**2 + ((yy - H*0.42)/(H*0.36))**2))[..., None]
    bg = base*(0.55 + 1.25*g)
    fy = int(H*floor_y)
    floor = np.clip((yy - fy)/(H - fy), 0, 1)[..., None]
    bg = bg*(1 - 0.35*floor) + (base*1.25)*0.35*floor*(yy >= fy)[..., None]
    horizon = np.exp(-((yy - fy)/6.0)**2)[..., None]*0.025
    vign = np.clip(1.12 - 0.75*(((xx-W/2)/(W*0.8))**2 + ((yy-H*0.45)/(H*0.7))**2), 0.3, 1)[..., None]
    return np.clip((bg + horizon)*vign, 0, 1)

def place(fr, rgb, al, cx, base_y, width):
    h0, w0 = rgb.shape[:2]; k = width/w0
    r = cv2.resize(rgb, (int(w0*k), int(h0*k)), interpolation=cv2.INTER_LANCZOS4)
    a = cv2.resize(al, (int(w0*k), int(h0*k)), interpolation=cv2.INTER_LINEAR)[..., None]
    bl = cv2.GaussianBlur(r, (0, 0), 1.3); r = np.clip(r + 0.5*(r - bl), 0, 1)
    h, w = r.shape[:2]; x0 = int(cx - w/2); y0 = int(base_y - h)
    # contact shadow on the floor
    sh = np.zeros((H, W), np.float32)
    cv2.ellipse(sh, (int(cx), int(base_y)-4), (int(w*0.52), int(h*0.03)+8), 0, 0, 360, 0.85, -1)
    fr *= (1 - cv2.GaussianBlur(sh, (0, 0), 14)[..., None])
    ys0, xs0 = max(y0, 0), max(x0, 0); ys1, xs1 = min(y0+h, H), min(x0+w, W)
    m = a[ys0-y0:ys1-y0, xs0-x0:xs1-x0]
    fr[ys0:ys1, xs0:xs1] = fr[ys0:ys1, xs0:xs1]*(1-m) + r[ys0-y0:ys1-y0, xs0-x0:xs1-x0]*m
    return fr

def cam(img, z, cx=0.5, cy=0.5):
    if abs(z - 1) < 1e-4: return img
    M = cv2.getRotationMatrix2D((W*cx, H*cy), 0, z)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)

def cover(img):
    h, w = img.shape[:2]; s = max(W/w, H/h)
    r = cv2.resize(img, (int(np.ceil(w*s)), int(np.ceil(h*s))), interpolation=cv2.INTER_LANCZOS4)
    y0 = (r.shape[0]-H)//2; x0 = (r.shape[1]-W)//2
    return r[y0:y0+H, x0:x0+W]

rng = np.random.default_rng(3)
GRAIN = [cv2.resize(rng.normal(0, 1, (H//2, W//2)).astype(np.float32), (W, H))[..., None] for _ in range(8)]

for sh in spec:
    if only and sh["id"] not in only: continue
    n = sh["n"]
    if sh["kind"] == "packshot":
        plate = studio_set(tuple(sh.get("tone", (0.075, 0.045, 0.11))), sh.get("floor", 0.66))
        for it in sh["items"]:
            rgb, al = load_cut(it["src"]); plate = place(plate, rgb, al, W*it["x"], H*it["base"], it["width"])
        still = plate
    else:  # generated still, already chosen and upscaled
        img = cv2.imread(sh["src"], cv2.IMREAD_COLOR).astype(np.float32)/255
        still = cover(img)
        bl = cv2.GaussianBlur(still, (0, 0), 1.6); still = np.clip(still + 0.45*(still - bl), 0, 1)   # gentle unsharp after 2.1x upscale
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p", f"{OUT}/{sh['id']}.mp4"], stdin=subprocess.PIPE)
    z0, z1 = sh.get("zoom", (1.0, 1.04)); cx, cy = sh.get("center", (0.5, 0.5))
    for i in range(n):
        u = smooth(i/max(n-1, 1)); fr = cam(still, z0 + (z1-z0)*u, cx, cy)
        fr = np.clip(fr + GRAIN[i % 8]*0.006, 0, 1)
        p.stdin.write((fr*255+0.5).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait(); print("shot", sh["id"], n, flush=True)

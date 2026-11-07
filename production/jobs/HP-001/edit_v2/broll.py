# Render cinematic B-roll shots for HP-001 V2 from REAL product pixels (temporal median of the source).
# No generated imagery of the products: only crop, scale, blur, light and motion.
import sys, json, subprocess, numpy as np, cv2
W, H, FPS = 1080, 1920, 30
MED = cv2.imread(sys.argv[1], cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535.0  # BGR float, 1080x1920 SDR
SPEC = json.load(open(sys.argv[2])); OUTDIR = sys.argv[3]
RECTS = {  # x0,y0,x1,y1 in source pixels (rotated 1080x1920)
 "leather": (770, 1168, 1062, 1540), "ivory": (44, 1160, 324, 1524),
 "box": (420, 1396, 708, 1592), "callig": (50, 796, 384, 1096),
 "carpet": (0, 1690, 1080, 1920), "curtain": (120, 70, 960, 760),
}
rng = np.random.default_rng(7)
def smooth(t): return t*t*(3-2*t)
def fill(img, w, h, z=1.0, cx=0.5, cy=0.5):
    ih, iw = img.shape[:2]; s = max(w/iw, h/ih)*z
    M = np.float32([[s, 0, w/2 - s*iw*cx], [0, s, h/2 - s*ih*cy]])
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
PADS = {  # (left, top, right, bottom): keep the speaker's blurred median ghost out of the product crops
 "leather": (4, 40, 18, 40), "ivory": (30, 40, 4, 40), "box": (40, 6, 40, 40), "callig": (30, 30, 30, 30)}
def crop(name, pad=0):
    x0, y0, x1, y1 = RECTS[name]
    l, t, r, b = PADS.get(name, (pad,)*4) if pad else (0, 0, 0, 0)
    return MED[max(y0-t,0):min(y1+b,1920), max(x0-l,0):min(x1+r,1080)].copy()
def grade(img, warm=1.0):
    img = np.clip(img, 0, 1)
    img = img*img*(3-2*img)*0.35 + img*0.65           # gentle S-curve
    img[..., 2] *= 1.0 + 0.04*warm; img[..., 0] *= 1.0 - 0.05*warm
    return np.clip(img, 0, 1)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = np.clip(1.15 - 0.85*(((xx-W/2)/(W*0.75))**2 + ((yy-H*0.48)/(H*0.62))**2), 0.25, 1)[..., None]
def particles(n=70):
    return dict(x=rng.uniform(0, W, n), y=rng.uniform(0, H, n), r=rng.uniform(1.2, 3.8, n),
                v=rng.uniform(8, 28, n), a=rng.uniform(0.15, 0.55, n), ph=rng.uniform(0, 6.28, n))
def draw_particles(fr, P, t):
    layer = np.zeros((H, W), np.float32)
    for x, y, r, v, a, ph in zip(P["x"], P["y"], P["r"], P["v"], P["a"], P["ph"]):
        yy_ = (y - v*t) % H; xx_ = x + 12*np.sin(t*0.7 + ph)
        cv2.circle(layer, (int(xx_), int(yy_)), int(r), float(a*(0.6+0.4*np.sin(t*2+ph))), -1, cv2.LINE_AA)
    layer = cv2.GaussianBlur(layer, (0, 0), 2.2)[..., None]
    gold = np.array([0.42, 0.74, 0.95], np.float32)
    return 1 - (1 - fr)*(1 - layer*gold)             # screen
def sweep(fr, t, dur, strength=0.22, angle=0.35):
    p = -0.4 + 1.8*smooth(min(max((t - 0.15*dur)/(0.75*dur), 0), 1))
    d = (xx/W*np.cos(angle) + yy/H*np.sin(angle)) - p
    band = np.exp(-(d/0.07)**2)[..., None]*strength
    warm = np.array([0.80, 0.92, 1.0], np.float32)
    return 1 - (1 - fr)*(1 - band*warm)
_RAYS = {}
def rays(fr, t, strength=0.30):
    # soft volumetric light from the top: few wide beams, heavily blurred, slowly breathing
    if "base" not in _RAYS:
        ang = np.arctan2(yy + H*0.25, xx - W*0.5)
        b = sum(np.exp(-((ang - a0)/0.035)**2) for a0 in np.linspace(1.15, 1.99, 7))
        r = np.sqrt((xx - W*0.5)**2 + (yy + H*0.25)**2)/H
        b = b*np.exp(-np.clip(r - 0.35, 0, None)*1.8)
        _RAYS["base"] = cv2.GaussianBlur(b.astype(np.float32), (0, 0), 18)
        glow = np.exp(-(((xx-W/2)/(W*0.45))**2 + ((yy-H*0.42)/(H*0.22))**2))
        _RAYS["glow"] = glow.astype(np.float32)
    l = (_RAYS["base"]*strength*(0.85 + 0.15*np.sin(t*1.3)) + _RAYS["glow"]*0.22)[..., None]*np.array([0.45, 0.78, 1.0], np.float32)
    return 1 - (1 - fr)*(1 - l)
def prep_fg(src, width):
    fg0 = grade(crop(src, 1))
    fh, fw = fg0.shape[:2]; k = width/fw
    fg = cv2.resize(fg0, (int(fw*k), int(fh*k)), interpolation=cv2.INTER_LANCZOS4)
    bl = cv2.GaussianBlur(fg, (0, 0), 1.4); fg = np.clip(fg + 0.55*(fg - bl), 0, 1)
    h2, w2 = fg.shape[:2]; e = int(min(w2, h2)*0.10)
    m = np.zeros((h2, w2), np.float32)
    cv2.rectangle(m, (e, e), (w2-e, h2-e), 1, -1); m = cv2.GaussianBlur(m, (0, 0), e*0.6)[..., None]
    ly, lx = np.mgrid[0:h2, 0:w2].astype(np.float32)
    inner = np.clip(1.08 - 0.55*(((lx-w2/2)/(w2*0.62))**2 + ((ly-h2/2)/(h2*0.62))**2), 0.45, 1)[..., None]
    return fg*inner, m
def paste(fr, fg, m, s, cx, cy):
    fgs = cv2.resize(fg, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR); ms = cv2.resize(m, None, fx=s, fy=s)
    if ms.ndim == 2: ms = ms[..., None]
    hh, ww = fgs.shape[:2]; x0, y0 = int(cx - ww/2), int(cy - hh/2)
    shadow = np.zeros((H, W), np.float32)
    cv2.rectangle(shadow, (x0+30, y0+50), (x0+ww-10, y0+hh+40), 0.65, -1)
    fr *= (1 - cv2.GaussianBlur(shadow, (0, 0), 38)[..., None])
    ys0, ys1, xs0, xs1 = max(y0, 0), min(y0+hh, H), max(x0, 0), min(x0+ww, W)
    sub = fgs[ys0-y0:ys1-y0, xs0-x0:xs1-x0]; mk = ms[ys0-y0:ys1-y0, xs0-x0:xs1-x0]
    fr[ys0:ys1, xs0:xs1] = fr[ys0:ys1, xs0:xs1]*(1 - mk) + sub*mk
    return fr
def velvet_bg(strength=0.18):
    return rays(grade(cv2.GaussianBlur(fill(crop("curtain"), W, H, 1.0), (0, 0), 10), 1.2)*0.45, 0, strength)
def render(shot):
    kind, dur = shot["kind"], shot["dur"]; n = int(round(dur*FPS))
    P = particles(shot.get("particles", 60))
    if kind == "product":
        fg0 = grade(crop(shot["src"], shot.get("pad", 14)))
        bg0 = rays(grade(cv2.GaussianBlur(fill(crop("curtain"), W, H, 1.0), (0, 0), 10), 1.2)*0.45, 0, 0.18)
        fh, fw = fg0.shape[:2]; k = shot.get("width", 760)/fw
        fg = cv2.resize(fg0, (int(fw*k), int(fh*k)), interpolation=cv2.INTER_LANCZOS4)
        bl = cv2.GaussianBlur(fg, (0, 0), 1.4); fg = np.clip(fg + 0.55*(fg - bl), 0, 1)   # mild unsharp
        h2, w2 = fg.shape[:2]
        e = int(min(w2, h2)*0.10)
        m = np.zeros((h2, w2), np.float32)
        cv2.rectangle(m, (e, e), (w2-e, h2-e), 1, -1); m = cv2.GaussianBlur(m, (0, 0), e*0.6)[..., None]
        ly, lx = np.mgrid[0:h2, 0:w2].astype(np.float32)
        inner = np.clip(1.08 - 0.55*(((lx-w2/2)/(w2*0.62))**2 + ((ly-h2/2)/(h2*0.62))**2), 0.45, 1)[..., None]
        fg = fg*inner
        sh = np.zeros((H, W), np.float32)
    out = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p", f"{OUTDIR}/{shot['id']}.mp4"], stdin=subprocess.PIPE)
    for i in range(n):
        t = i/FPS; u = smooth(i/max(n-1, 1))
        z0, z1 = shot.get("zoom", (1.0, 1.07))
        z = z0 + (z1 - z0)*u
        if kind == "product":
            bg = fill(bg0, W, H, 1.04 + 0.04*u)
            s = z; fgs = cv2.resize(fg, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR); ms = cv2.resize(m, None, fx=s, fy=s)[..., None]
            hh, ww = fgs.shape[:2]
            cx = W//2 + int(shot.get("drift", (0, 0))[0]*u); cy = int(H*shot.get("cy", 0.47)) + int(shot.get("drift", (0, 0))[1]*u)
            x0, y0 = cx - ww//2, cy - hh//2
            fr = bg.copy()
            shadow = np.zeros((H, W), np.float32)
            cv2.rectangle(shadow, (x0+30, y0+50), (x0+ww-10, y0+hh+40), 0.65, -1)
            shadow = cv2.GaussianBlur(shadow, (0, 0), 38)[..., None]; fr *= (1 - shadow)
            ys0, ys1, xs0, xs1 = max(y0, 0), min(y0+hh, H), max(x0, 0), min(x0+ww, W)
            sub = fgs[ys0-y0:ys1-y0, xs0-x0:xs1-x0]; mk = ms[ys0-y0:ys1-y0, xs0-x0:xs1-x0]
            fr[ys0:ys1, xs0:xs1] = fr[ys0:ys1, xs0:xs1]*(1 - mk) + sub*mk
        elif kind == "multi":
            if i == 0:
                items = [(prep_fg(it["src"], it["width"]), it) for it in shot["items"]]
                bgm = velvet_bg()
            fr = fill(bgm, W, H, 1.03 + 0.03*u)
            for (fgm, it) in items:
                fr = paste(fr, fgm[0], fgm[1], z*it.get("scale", 1.0), W*it["x"] + it.get("dx", 0)*u, H*it["y"])
        elif kind == "textbg":   # blurred real product as warm backdrop for big typography
            if i == 0:
                src = grade(crop(shot["src"], 1))
                tb = cv2.GaussianBlur(fill(src, W, H, 1.0), (0, 0), shot.get("blur", 22))*shot.get("dim", 0.42)
            fr = fill(tb, W, H, z)
            if shot.get("rays"): fr = rays(fr, t, 0.2)
        else:  # backdrop card: curtain or carpet texture, darkened, for typography
            src = grade(crop(shot["src"]), 1.2)
            fr = cv2.GaussianBlur(fill(src, W, H, z, 0.5, 0.5), (0, 0), shot.get("blur", 6))*shot.get("dim", 0.55)
            if shot.get("rays"): fr = rays(fr, t)
        rf = shot.get("rack", 0)
        if rf and t < rf:
            sg = 9*(1 - smooth(t/rf))
            if sg > 0.3: fr = cv2.GaussianBlur(fr, (0, 0), sg)
        if shot.get("sweep", True) and kind in ("product", "multi"): fr = sweep(fr, t, dur)
        fr = fr*VIG
        fr = draw_particles(fr, P, t)
        fade = shot.get("fade_in", 0)
        if fade and t < fade: fr *= smooth(t/fade)
        grain = rng.normal(0, 0.008, (H//2, W//2)).astype(np.float32)
        fr = np.clip(fr + cv2.resize(grain, (W, H))[..., None], 0, 1)
        out.stdin.write((fr*255 + 0.5).astype(np.uint8).tobytes())
    out.stdin.close(); out.wait()
    print("rendered", shot["id"], n, flush=True)
ids = sys.argv[4].split(",") if len(sys.argv) > 4 else None
for s in SPEC:
    if ids is None or s["id"] in ids: render(s)

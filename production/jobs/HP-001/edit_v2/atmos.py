# Procedural ambience + soft SFX (no third-party audio). Output: 48 kHz stereo WAV.
import sys, json, numpy as np, wave
from scipy.signal import butter, sosfilt
SR = 48000
spec = json.load(open(sys.argv[1])); out = sys.argv[2]
N = int(spec["duration"]*SR); rng = np.random.default_rng(11)
t = np.arange(N)/SR
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)
def lp(x, f, order=2): return sosfilt(butter(order, f, "lowpass", fs=SR, output="sos"), x)
def db(x): return 10**(x/20)
L = np.zeros(N); R = np.zeros(N)
# 1) air bed: two decorrelated pink-ish noises, low-passed, slow breathing
for ch in (L, R):
    w = rng.standard_normal(N)
    pink = lp(w, 900) + 0.5*lp(w, 250)
    pink /= np.max(np.abs(pink)) + 1e-9
    breath = 0.75 + 0.25*np.sin(2*np.pi*0.07*t + rng.uniform(0, 6))
    ch += pink*breath*db(spec.get("bed_db", -46))
fade = np.clip(np.minimum(t/1.2, (spec["duration"]-t)/1.5), 0, 1); L *= fade; R *= fade
def place(sig, at, gain_db, pan=0.0):
    i = int(at*SR); n = min(len(sig), N-i)
    if n <= 0 or i < 0: return
    g = db(gain_db); L[i:i+n] += sig[:n]*g*(1-pan)**0.5; R[i:i+n] += sig[:n]*g*(1+pan)**0.5
def whoosh(d=0.7):
    n = int(d*SR); x = rng.standard_normal(n); tt = np.arange(n)/n
    env = np.sin(np.pi*tt)**2.2
    # sweep a band upwards through the swell
    y = np.zeros(n); seg = 8
    for k in range(seg):
        a, b = k*n//seg, (k+1)*n//seg; f = 300 + 2200*(k/seg)
        y[a:b] = bp(x, f*0.6, min(f*1.6, 20000))[a:b]
    y = y*env; return y/np.max(np.abs(y))
def impact(d=1.6):
    n = int(d*SR); tt = np.arange(n)/SR
    f = 62*np.exp(-tt*1.2) + 36
    ph = 2*np.pi*np.cumsum(f)/SR
    y = np.sin(ph)*np.exp(-tt*2.6) + 0.25*lp(rng.standard_normal(n), 180)*np.exp(-tt*8)
    return y/np.max(np.abs(y))
def shimmer(d=2.6):
    n = int(d*SR); tt = np.arange(n)/SR
    y = bp(rng.standard_normal(n), 5000, 11000)*np.exp(-tt*1.4)*(1-np.exp(-tt*25))
    return y/np.max(np.abs(y))
for ev in spec["events"]:
    sig = {"whoosh": whoosh, "impact": impact, "shimmer": shimmer}[ev["type"]]()
    place(sig, ev["t"], ev.get("db", -30), ev.get("pan", 0.0))
st = np.stack([L, R], 1); st = np.clip(st, -1, 1)
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st*32767).astype(np.int16).tobytes())
print("atmos ok", spec["duration"])

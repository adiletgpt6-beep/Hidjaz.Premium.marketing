# V4 music bed: self-composed slow sustained chord pad (no noise layer, no percussion, no melody, no SFX).
# Chord changes are placed on the emotional beats of the edit. 48 kHz stereo WAV.
import sys, json, numpy as np, wave
from scipy.signal import butter, sosfilt
SR = 48000
spec = json.load(open(sys.argv[1])); OUT = sys.argv[2]
D = spec["duration"]; N = int(D*SR); t = np.arange(N)/SR; rng = np.random.default_rng(9)
def hz(m): return 440.0*2**((m-69)/12)
def lp(x, f): return sosfilt(butter(2, f, "lowpass", fs=SR, output="sos"), x)
def tone(f, n=3, det=0.0016):
    out = np.zeros(N)
    for k in range(n):
        ph = rng.uniform(0, 2*np.pi); fk = f*(1 + det*(k-(n-1)/2))
        vib = 1 + 0.0007*np.sin(2*np.pi*(0.13+0.04*k)*t + ph)
        p = 2*np.pi*fk*np.cumsum(vib)/SR + ph
        out += np.sin(p) + 0.22*np.sin(2*p) + 0.07*np.sin(3*p)
    return out/n
# chords as MIDI notes (bass + voicing); times in seconds where each chord is fully in
CH = spec["chords"]
L = np.zeros(N); R = np.zeros(N)
cache = {}
for idx, (t0, notes) in enumerate(CH):
    t1 = CH[idx+1][0] if idx+1 < len(CH) else D + 2
    a0, a1 = t0 - 1.2, t1 + 0.4                       # 1.2 s crossfade between chords
    env = np.clip((t - a0)/1.2, 0, 1)*np.clip((a1 - t)/1.6, 0, 1); env = env*env*(3-2*env)
    for j, m in enumerate(notes):
        if m not in cache: cache[m] = tone(hz(m))
        g = 0.55 if j == 0 else 0.30/(1 + 0.25*(j-1)); pan = [-0.25, 0.3, -0.15, 0.2, 0.0][j % 5]
        L += cache[m]*env*g*(1-pan); R += cache[m]*env*g*(1+pan)
L, R = lp(L, 1700), lp(R, 1700)
keys = np.array(spec["keys"], dtype=float); env_db = np.interp(t, keys[:, 0], keys[:, 1])
k = int(0.3*SR); ker = np.hanning(k); ker /= ker.sum(); env = np.convolve(10**(env_db/20), ker, mode="same")
st = np.stack([L, R], 1); st /= np.max(np.abs(st)) + 1e-9; st *= env[:, None]
st[:int(0.8*SR)] *= np.linspace(0, 1, int(0.8*SR))[:, None]
with wave.open(OUT, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(st, -1, 1)*32767).astype(np.int16).tobytes())
print("pad v4 ok", D)

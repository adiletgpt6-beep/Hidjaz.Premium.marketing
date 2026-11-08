# Self-synthesised warm ambient bed (no third-party audio, no melody, no transition SFX). 48 kHz stereo WAV.
# Sustained D/A drone with slow harmonic motion and a soft air layer; swells are given as (time, gain_db) keys.
import sys, json, numpy as np, wave
from scipy.signal import butter, sosfilt
SR = 48000
spec = json.load(open(sys.argv[1])); OUT = sys.argv[2]
D = spec["duration"]; N = int(D*SR); t = np.arange(N)/SR
rng = np.random.default_rng(5)
def lp(x, f): return sosfilt(butter(2, f, "lowpass", fs=SR, output="sos"), x)
def voice(freq, det=0.0012, n=4):
    out = np.zeros(N)
    for k in range(n):
        f = freq*(1 + det*(k - (n-1)/2)); ph = rng.uniform(0, 2*np.pi)
        vib = 1 + 0.0009*np.sin(2*np.pi*(0.11 + 0.03*k)*t + ph)
        out += np.sin(2*np.pi*f*np.cumsum(vib)/SR + ph)*(0.6 + 0.4*np.sin(2*np.pi*0.05*t + k))
    return out/n
L = np.zeros(N); R = np.zeros(N)
# root D2, fifth A2, octave D3, soft F3 (minor colour) entering later, high A4 shimmer very quiet
layers = [(73.42, 0.55, -0.3), (110.0, 0.42, 0.3), (146.83, 0.30, -0.15), (174.61, 0.16, 0.2), (220.0, 0.10, 0.0)]
for f, g, pan in layers:
    v = voice(f)
    # add 2nd/3rd harmonics softly for warmth (body), then low-pass for darkness
    v = v + 0.25*voice(2*f, 0.0015, 3) + 0.08*voice(3*f, 0.002, 2)
    v = lp(v, 1400)
    L += v*g*(1 - pan); R += v*g*(1 + pan)
# F3 colour enters gently after the hook
fade_in_f = np.clip((t - 6.0)/3.0, 0, 1)
air = lp(rng.standard_normal(N), 700)*0.05
L += air; R += lp(rng.standard_normal(N), 700)*0.05
# master envelope from keys (dB), smoothly interpolated
keys = np.array(spec["keys"], dtype=float)
env_db = np.interp(t, keys[:, 0], keys[:, 1]); env = 10**(env_db/20)
k = int(0.25*SR); ker = np.hanning(k); ker /= ker.sum(); env = np.convolve(env, ker, mode="same")
st = np.stack([L, R], 1); st /= np.max(np.abs(st)) + 1e-9
st *= env[:, None]
st[:int(0.6*SR)] *= np.linspace(0, 1, int(0.6*SR))[:, None]
with wave.open(OUT, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(st, -1, 1)*32767).astype(np.int16).tobytes())
print("pad ok", D)

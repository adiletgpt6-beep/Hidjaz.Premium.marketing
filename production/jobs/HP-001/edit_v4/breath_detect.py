# Detect isolated unvoiced events (breaths/exhales/noises) in a voice track. Prints candidates; --json writes them.
import sys, json, wave, numpy as np, librosa
P = sys.argv[1]
w = wave.open(P); sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)/32768
if w.getnchannels() == 2: a = a[::2]
y = librosa.resample(a, orig_sr=sr, target_sr=16000); hop = 160
f0, vflag, _ = librosa.pyin(y, fmin=70, fmax=350, sr=16000, frame_length=1024, hop_length=hop)
rms = librosa.feature.rms(y=y, frame_length=480, hop_length=hop)[0][:len(vflag)]; db = 20*np.log10(rms+1e-9)
cand = (~vflag) & (db > -54)
vidx = np.where(vflag)[0]
out = []; i = 0
while i < len(cand):
    if not cand[i]: i += 1; continue
    j = i
    while j < len(cand) and cand[j]: j += 1
    dur = (j-i)*0.01
    prev_v = vidx[vidx < i]; next_v = vidx[vidx >= j]
    gl = (i - prev_v[-1])*0.01 if len(prev_v) else 9; gr = (next_v[0] - j)*0.01 if len(next_v) else 9
    if dur >= 0.10 and gl >= 0.05 and gr >= 0.05:
        out.append(dict(t0=round(i*0.01, 2), t1=round(j*0.01, 2), peak=round(float(db[i:j].max()), 1), gap_l=round(gl, 2), gap_r=round(gr, 2)))
    i = j
words = json.load(open(sys.argv[2])) if len(sys.argv) > 2 and sys.argv[2].endswith(".json") else None
for e in out:
    ctx = ""
    if words:
        before = [w_["w"].strip() for w_ in words if w_["e"] <= e["t0"] + 0.15][-1:] ; after = [w_["w"].strip() for w_ in words if w_["s"] >= e["t1"] - 0.15][:1]
        ctx = f"  between {before} and {after}"
    print(e, ctx)
if "--json" in sys.argv: json.dump(out, open(sys.argv[-1], "w"), indent=1)

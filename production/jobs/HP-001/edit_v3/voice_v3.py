# Assemble the V2 voice track from the selected takes (source seconds), level-matched, with short crossfades.
import sys, json, wave, numpy as np
SRC48, OUT = sys.argv[1], sys.argv[2]
SR = 48000
# id, src_in, src_out, gap_after (s of room tone before next piece), note
PIECES = [
 ("H", 16.84, 22.50, 0.40, "А вы когда-нибудь задумывались, какой подарок действительно принесёт пользу вашему близкому человеку? (take 16.9s, continuous, no splice)"),
 ("L2a", 140.36, 141.10, 0.00, "Представьте,  (take 140.4s; 0.76s hesitation trimmed, hidden under B-roll)"),
 ("L2b", 141.58, 144.24, 0.60, "вы дарите не просто книгу, а священный Коран."),
 ("L3", 311.00, 315.08, 0.70, "Подарок, к которому человек будет возвращаться снова и снова. (take 311.0s)"),
 ("L4", 158.52, 161.66, 0.75, "Для родителей, для любимых, для самых дорогих людей. (take 158.5s)"),
 ("L5a", 333.86, 336.88, 0.00, "Подарите то, что будет напоминать о вас с (take 333.9s)"),
 ("L5b", 337.40, 339.06, 0.50, "каждой прочитанной страницей. (0.52s hesitation trimmed, hidden under B-roll)"),
 ("L6a", 340.14, 341.33, 0.00, "Напишите нам в WhatsApp, и (take 340.1s)"),
 ("L6b", 341.70, 344.34, 0.00, "мы подберём для вас подходящий Коран. (0.37s pause trimmed at the shot change)"),
]
w = wave.open(SRC48); assert w.getframerate() == SR
a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)/32768
def speech_rms(x):
    f = 1024; fr = x[:len(x)//f*f].reshape(-1, f); r = np.sqrt((fr**2).mean(1)+1e-12)
    loud = r[r > np.percentile(r, 60)]; return float(np.sqrt((loud**2).mean()))
segs = [a[int(s*SR):int(e*SR)].copy() for _, s, e, _, _ in PIECES]
# level-match per LINE (pieces of one take share a gain) to the median line level
lines = {}
for (pid, *_), x in zip(PIECES, segs): lines.setdefault(pid.rstrip("ab"), []).append(x)
lvl = {k: speech_rms(np.concatenate(v)) for k, v in lines.items()}
ref = float(np.median(list(lvl.values())))
XF = int(0.012*SR)
out = np.zeros(0, np.float32); place = []
for (pid, s, e, gap, note), x in zip(PIECES, segs):
    key = pid.rstrip("ab")
    g = ref/lvl[key]; x = x*g
    ramp = np.linspace(0, 1, XF, dtype=np.float32); x[:XF] *= ramp; x[-XF:] *= ramp[::-1]
    start = len(out)/SR
    if len(out) >= XF and gap == 0 and place and place[-1]["gap"] == 0:
        start -= XF/SR; out[-XF:] += x[:XF]; out = np.concatenate([out, x[XF:]])
    else:
        out = np.concatenate([out, x])
    place.append({"id": pid, "src_in": s, "src_out": e, "out_in": round(start, 4), "out_out": round(len(out)/SR, 4), "gain_db": round(20*np.log10(g), 2), "gap": gap, "note": note})
    out = np.concatenate([out, np.zeros(int(gap*SR), np.float32)])
with wave.open(OUT, "wb") as o:
    o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR)
    o.writeframes((np.clip(out, -1, 1)*32767).astype(np.int16).tobytes())
json.dump({"pieces": place, "voice_dur": round(len(out)/SR, 4), "line_levels_db": {k: round(20*np.log10(v), 2) for k, v in lvl.items()}}, open(OUT + ".json", "w"), ensure_ascii=False, indent=1)
for p in place: print(p["id"], p["out_in"], p["out_out"], p["gain_db"])
print("dur", len(out)/SR)

# Score every take of every script line: text accuracy, fluency, pauses, pitch range, ASR confidence, eye contact.
import sys, json, wave, subprocess, re, difflib
import numpy as np, librosa, cv2
from faster_whisper import WhisperModel
SRC, WAV, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
LINES = {
 "L1": "а вы когда-нибудь задумывались какой подарок действительно принесет пользу вашему близкому человеку",
 "L2": "представьте вы дарите не просто книгу а священный коран",
 "L3": "подарок к которому человек будет возвращаться снова и снова",
 "L4": "для родителей для любимых для самых дорогих людей",
 "L5": "подарите то что будет напоминать о вас с каждой прочитанной страницей",
 "L6": "напишите нам в whatsapp и мы подберем для вас подходящий коран",
}
TAKES = {
 "L1": [(16.5,22.8),(79.9,86.3),(133.2,139.9),(237.9,248.5),(283.8,291.0),(296.9,305.4)],
 "L2": [(85.9,90.4),(139.7,144.3),(170.6,172.9),(205.7,210.5),(248.7,254.9),(305.2,309.9)],
 "L3": [(90.3,94.1),(150.0,157.6),(172.6,175.9),(210.5,214.4),(260.4,266.8),(310.7,315.0)],
 "L4": [(94.3,98.9),(157.5,161.7),(175.7,178.3),(215.1,219.2),(266.6,270.7),(315.6,320.6)],
 "L5": [(99.3,104.4),(161.8,166.2),(178.2,181.4),(221.9,225.9),(229.5,233.5),(273.6,278.6),(333.6,339.2)],
 "L6": [(104.7,110.0),(181.2,185.6),(339.7,344.4)],
}
wf = wave.open(WAV); sr = wf.getframerate()
audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768
model = WhisperModel("large-v3", device="cpu", compute_type="int8", cpu_threads=4)
fc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
ec = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml")
norm = lambda s: re.sub(r"[^\w ]", "", s.lower().replace("ё", "е").replace("-", "")).replace("куран", "коран").split()
def gaze(a, b):
    W, H = 520, 640
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{a}", "-t", f"{b-a}", "-i", SRC, "-vf", f"fps=5,crop=520:640:290:700,format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W)
    ok = 0
    for f in fr:
        faces = fc.detectMultiScale(f, 1.1, 5, minSize=(110, 110))
        if len(faces) == 0: continue
        x, y, w, h = max(faces, key=lambda r: r[2]*r[3])
        eyes = ec.detectMultiScale(f[y:y+h//2+h//8, x:x+w], 1.05, 4, minSize=(18, 18))
        ok += len(eyes) >= 2
    return ok / max(len(fr), 1)
res = {}
for L, takes in TAKES.items():
    ref = norm(LINES[L]); res[L] = []
    for (a, b) in takes:
        seg = audio[int(a*sr):int(b*sr)]
        segs, _ = model.transcribe(seg, language="ru", word_timestamps=True, beam_size=5, condition_on_previous_text=False, vad_filter=False)
        words = [w for s in segs for w in s.words]
        text = " ".join(w.word.strip() for w in words)
        hyp = norm(text)
        sim = difflib.SequenceMatcher(None, ref, hyp).ratio()
        if not words: res[L].append({"take": [a, b], "text": ""}); continue
        s0, s1 = words[0].start, words[-1].end
        sp = seg[int(s0*sr):int(s1*sr)]
        rms = librosa.feature.rms(y=sp, frame_length=800, hop_length=160)[0]
        db = 20*np.log10(rms + 1e-9); thr = np.percentile(db, 90) - 30
        sil = db < thr; runs, cur = [], 0
        for v in sil:
            if v: cur += 1
            else:
                if cur: runs.append(cur)
                cur = 0
        pauses = [r*0.01 for r in runs if r*0.01 >= 0.25]
        f0, vf, _ = librosa.pyin(sp, fmin=70, fmax=320, sr=sr, frame_length=1024, hop_length=160)
        f0 = f0[~np.isnan(f0)]
        st = 12*np.log2(f0/np.median(f0)) if len(f0) > 10 else np.array([0])
        res[L].append({"take": [round(a+s0, 2), round(a+s1, 2)], "text": text, "match": round(sim, 3),
            "dur": round(s1-s0, 2), "rate_wps": round(len(words)/(s1-s0), 2),
            "max_pause": round(max(pauses, default=0), 2), "sum_pause": round(sum(pauses), 2),
            "pitch_range_st": round(float(np.percentile(st, 95)-np.percentile(st, 5)), 1),
            "asr_conf": round(float(np.mean([w.probability for w in words])), 3),
            "level_db": round(float(np.percentile(db, 90)), 1),
            "eye_contact": None})
        r = res[L][-1]; print(L, r, flush=True)
json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)

import sys, json, time
from faster_whisper import WhisperModel
audio, out, model_name = sys.argv[1], sys.argv[2], sys.argv[3]
lang = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "auto" else None
t=time.time()
import wave, numpy as np
wf=wave.open(audio);audio=np.frombuffer(wf.readframes(wf.getnframes()),dtype=np.int16).astype(np.float32)/32768.0
m = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=4)
segs, info = m.transcribe(audio, language=lang, word_timestamps=True, vad_filter=True, beam_size=5)
print("lang", info.language, info.language_probability, flush=True)
res=[]
for s in segs:
    res.append({"start":s.start,"end":s.end,"text":s.text,"words":[{"s":w.start,"e":w.end,"w":w.word,"p":w.probability} for w in s.words]})
    print(f"{s.start:7.2f}-{s.end:7.2f} {s.text}", flush=True)
json.dump({"language":info.language,"segments":res}, open(out,"w"), ensure_ascii=False, indent=1)
print("done", time.time()-t)

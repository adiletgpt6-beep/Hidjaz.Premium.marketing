# HP-001 / VID-001 — V2 "cinematic" edit builder.
# Inputs: source MOV, voice_raw.wav (+.json placements), voice_asr.json (word timings), median16.png (product plates).
import sys, os, json, subprocess, re
S = sys.argv[1]  # scratchpad root
SRC = f"{S}/src/source.mov"; V2 = f"{S}/v2"; SCR = f"{S}/scripts"
FPS = 30; TOTAL = 29.0
place = json.load(open(f"{V2}/voice_raw.wav.json"))["pieces"]
P = {p["id"]: p for p in place}

# ---------- shot list (output seconds) ----------
SHOTS = [
 dict(id="s01", a=0.00,  b=1.43,  type="spk", piece="H1",  z=(1.20, 1.25)),
 dict(id="s02", a=1.43,  b=2.52,  type="broll", spec=dict(kind="product", src="box", width=940, zoom=(1.0, 1.06), rack=0.25)),
 dict(id="s03", a=2.52,  b=5.62,  type="spk", piece="H2",  z=(1.06, 1.10)),
 dict(id="s04", a=5.62,  b=8.10,  type="broll", spec=dict(kind="product", src="ivory", width=800, zoom=(1.0, 1.07), rack=0.45, drift=(0, -30))),
 dict(id="s05", a=8.10,  b=9.40,  type="broll", spec=dict(kind="product", src="leather", width=820, zoom=(1.03, 1.10), rack=0.2)),
 dict(id="s06", a=9.40,  b=11.95, type="spk", piece="L3",  z=(1.14, 1.19)),
 dict(id="s07", a=11.95, b=13.80, type="broll", spec=dict(kind="card", src="curtain", rays=True, dim=0.5, zoom=(1.0, 1.05))),
 dict(id="s08", a=13.80, b=14.80, type="broll", spec=dict(kind="textbg", src="ivory", rays=True, dim=0.26, zoom=(1.0, 1.05))),
 dict(id="s09", a=14.80, b=15.84, type="broll", spec=dict(kind="textbg", src="box", rays=True, dim=0.34, zoom=(1.05, 1.0))),
 dict(id="s10", a=15.84, b=17.86, type="broll", spec=dict(kind="multi", zoom=(1.0, 1.05), items=[
        dict(src="ivory", width=410, x=0.275, y=0.40), dict(src="leather", width=410, x=0.725, y=0.40),
        dict(src="box", width=560, x=0.50, y=0.635)])),
 dict(id="s11", a=17.86, b=20.22, type="spk", piece="L5a", z=(1.18, 1.23)),
 dict(id="s12", a=20.22, b=22.18, type="broll", spec=dict(kind="product", src="callig", width=980, zoom=(1.02, 1.10), drift=(-40, 0), rack=0.3)),
 dict(id="s13", a=22.18, b=23.37, type="spk", piece="L6a", z=(1.08, 1.11)),
 dict(id="s14", a=23.37, b=26.10, type="broll", spec=dict(kind="multi", zoom=(1.0, 1.06), items=[
        dict(src="ivory", width=470, x=0.285, y=0.48, dx=-10), dict(src="leather", width=470, x=0.715, y=0.48, dx=10)])),
 dict(id="s15", a=26.10, b=29.00, type="broll", spec=dict(kind="card", src="curtain", rays=True, dim=0.42, zoom=(1.0, 1.04), particles=90)),
]
fr = lambda t: int(round(t*FPS))
for s in SHOTS: s["n"] = fr(s["b"]) - fr(s["a"])
assert sum(s["n"] for s in SHOTS) == fr(TOTAL)

# ---------- B-roll ----------
spec = []
for s in SHOTS:
    if s["type"] == "broll":
        d = dict(s["spec"]); d["id"] = s["id"]; d["dur"] = s["n"]/FPS; d.setdefault("pad", 1); spec.append(d)
json.dump(spec, open(f"{V2}/broll_spec.json", "w"), indent=1)
ONLY = [a.split("=",1)[1] for a in sys.argv if a.startswith("--broll=")]
if "--skip-broll" not in sys.argv:
    subprocess.run(["python3", "-I", f"{SCR}/broll.py", f"{S}/broll/median16.png", f"{V2}/broll_spec.json", V2] + ONLY, check=True)

# ---------- speaker shots ----------
TM = "zscale=t=linear:npl=203,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv:p=bt709,format=yuv420p"
GRADE = "eq=contrast=1.07:brightness=-0.025:saturation=1.04,colorbalance=rs=0.03:gs=0.0:bs=-0.035:rm=0.02:bm=-0.02,vignette=angle=PI/4.6,noise=alls=3:allf=t"
FX, FY = 550, 1000
for s in SHOTS:
    if s["type"] != "spk": continue
    if "--skip-spk" in sys.argv and os.path.exists(f"{V2}/{s['id']}.mp4"): continue
    p = P[s["piece"]]; src_t = p["src_in"] + (s["a"] - p["out_in"]); D = s["n"]/FPS
    z0, z1 = s["z"]; z = f"({z0}+({z1}-{z0})*(3*pow(min(t/{D:.3f},1),2)-2*pow(min(t/{D:.3f},1),3)))"
    vf = (f"fps={FPS},{TM},setpts=PTS-STARTPTS,"
          f"scale=w='2*trunc(1080*{z}/2)':h='2*trunc(1920*{z}/2)':eval=frame:flags=lanczos,"
          f"crop=1080:1920:x='min(max({FX}*iw/1080-540,0),iw-1080)':y='min(max({FY}*ih/1920-960,0),ih-1920)',setsar=1,{GRADE}")
    s["src_t"] = round(src_t, 3)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{src_t:.3f}", "-i", SRC, "-an", "-vf", vf, "-frames:v", str(s["n"]),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p", f"{V2}/{s['id']}.mp4"], check=True)
    print("speaker", s["id"], s["piece"], src_t, flush=True)

# ---------- concat video ----------
with open(f"{V2}/concat.txt", "w") as f:
    for s in SHOTS: f.write(f"file '{V2}/{s['id']}.mp4'\n")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{V2}/concat.txt", "-c", "copy", f"{V2}/video_nocap.mp4"], check=True)

# ---------- captions / typography (ASS) ----------
asr = json.load(open(f"{V2}/voice_asr.json"))
ws = []
for w in [w for sg in asr["segments"] for w in sg["words"]]:
    if w["w"].strip().startswith("-") and ws: ws[-1]["w"] += w["w"].strip(); ws[-1]["e"] = w["e"]
    else: ws.append(dict(w))
assert len(ws) == 60, len(ws)
# snap ASR word onsets that fall inside a detected pause to the real speech onset (end of that pause)
sil = subprocess.run(["ffmpeg", "-hide_banner", "-i", f"{V2}/voice_raw.wav", "-af", "silencedetect=n=-45dB:d=0.08", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
ss = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", sil)]; se = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", sil)]
pauses = []
for a_, b_ in zip(ss, se):
    if pauses and a_ - pauses[-1][1] < 0.03: pauses[-1] = (pauses[-1][0], b_)
    else: pauses.append((a_, b_))
for w in ws:
    for a_, b_ in pauses:
        if a_ - 0.08 <= w["s"] < b_ and b_ - w["s"] < 0.6: w["s"] = b_; break
json.dump(ws, open(f"{V2}/words_snapped.json", "w"), ensure_ascii=False, indent=1)
# chunks: (first_word, last_word, TEXT, highlight, mode) ; mode "cap" = bottom caption, "big" = handled by a big card
CH = [
 (0, 2, "А ВЫ\\NКОГДА-НИБУДЬ", "КОГДА-НИБУДЬ"), (3, 3, "ЗАДУМЫВАЛИСЬ,", "ЗАДУМЫВАЛИСЬ,"),
 (4, 5, "КАКОЙ ПОДАРОК", "ПОДАРОК"), (6, 7, "ДЕЙСТВИТЕЛЬНО\\NПРИНЕСЁТ", "ДЕЙСТВИТЕЛЬНО"), (8, 8, "ПОЛЬЗУ", "ПОЛЬЗУ"),
 (9, 11, "ВАШЕМУ БЛИЗКОМУ\\NЧЕЛОВЕКУ?", "БЛИЗКОМУ"),
 (12, 12, "ПРЕДСТАВЬТЕ,", "ПРЕДСТАВЬТЕ,"), (13, 14, "ВЫ ДАРИТЕ", "ДАРИТЕ"), (15, 17, "НЕ ПРОСТО\\NКНИГУ,", "КНИГУ,"),
 (18, 20, "А СВЯЩЕННЫЙ\\NКОРАН.", "КОРАН."),
 (21, 21, "ПОДАРОК,", "ПОДАРОК,"), (22, 24, "К КОТОРОМУ\\NЧЕЛОВЕК", "ЧЕЛОВЕК"), (25, 26, "БУДЕТ\\NВОЗВРАЩАТЬСЯ", "ВОЗВРАЩАТЬСЯ"),
 (27, 29, None, None), (30, 31, None, None), (32, 33, None, None),
 (34, 35, "ДЛЯ САМЫХ", "САМЫХ"), (36, 37, "ДОРОГИХ ЛЮДЕЙ.", "ДОРОГИХ"),
 (38, 39, "ПОДАРИТЕ ТО,", "ПОДАРИТЕ"), (40, 42, "ЧТО БУДЕТ\\NНАПОМИНАТЬ", "НАПОМИНАТЬ"), (43, 44, "О ВАС", "ВАС"),
 (45, 46, "С КАЖДОЙ", "КАЖДОЙ"), (47, 48, "ПРОЧИТАННОЙ\\NСТРАНИЦЕЙ.", "СТРАНИЦЕЙ."),
 (49, 50, "НАПИШИТЕ НАМ", "НАПИШИТЕ"), (51, 52, "В WHATSAPP,", "WHATSAPP,"), (53, 55, "И МЫ\\NПОДБЕРЁМ", "ПОДБЕРЁМ"),
 (56, 57, "ДЛЯ ВАС", "ВАС"), (58, 59, "ПОДХОДЯЩИЙ\\NКОРАН.", "КОРАН."),
]
def ts(t):
    t = max(t, 0); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
GOLD = "&H3DC1F2&"  # #F2C13D
starts = [max(ws[a]["s"] - 0.06, 0) for a, *_ in CH]
ev = []
for k, (a, b, text, hl) in enumerate(CH):
    if text is None: continue
    st = starts[k]; en = starts[k+1] if k+1 < len(CH) else 26.05
    parts = []
    for tok in text.replace("\\N", " \\N ").split(" "):
        if tok == "\\N": parts.append("\\N"); continue
        parts.append(f"{{\\c{GOLD}}}{tok}{{\\c&HFFFFFF&}}" if tok == hl else tok)
    body = " ".join(parts).replace(" \\N ", "\\N")
    ev.append(f"Dialogue: 2,{ts(st)},{ts(en)},Cap,,0,0,0,,{{\\pos(540,1478)\\fscx86\\fscy86\\t(0,110,\\fscx100\\fscy100)\\fad(40,0)}}{body}")
def big(t0, t1, lines, y=900, size=150):
    out = []
    for j, (txt, col, delay) in enumerate(lines):
        yy = y + j*int(size*1.05) - (len(lines)-1)*int(size*1.05)//2
        out.append(f"Dialogue: 3,{ts(t0+delay)},{ts(t1)},Big,,0,0,0,,{{\\pos(540,{yy})\\fs{size}\\c{col}\\fscx80\\fscy80\\t(0,140,\\fscx100\\fscy100)\\fad(60,0)}}{txt}")
    return out
W_ = lambda i: ws[i]["s"]
ev += big(11.95, 13.80, [("СНОВА", GOLD, 0.0), ("И СНОВА", "&HFFFFFF&", max(W_(28) - 0.06 - 11.95, 0.2))], size=170)
ev += big(13.80, 14.80, [("ДЛЯ", "&HFFFFFF&", 0), ("РОДИТЕЛЕЙ", GOLD, 0.08)], size=150)
ev += big(14.80, 15.84, [("ДЛЯ", "&HFFFFFF&", 0), ("ЛЮБИМЫХ", GOLD, 0.08)], size=150)
def chip(t0, t1, text, y=330):
    return [f"Dialogue: 4,{ts(t0)},{ts(t1)},Chip,,0,0,0,,{{\\pos(540,{y})\\fad(80,80)\\t(0,120,\\fscx100\\fscy100)\\fscx90\\fscy90}}{text}"]
ev += chip(0.05, 1.43, "HIDJAZ PREMIUM")
ev += chip(1.50, 2.52, "ПОДАРОК")
ev += chip(8.16, 9.40, "СВЯЩЕННЫЙ КОРАН")
ev += chip(22.24, 23.37, "WHATSAPP")
# end card
T0 = 26.10
ev.append(f"Dialogue: 3,{ts(T0+0.15)},{ts(TOTAL)},Brand,,0,0,0,,{{\\pos(540,880)\\fad(500,350)\\blur0.5}}Hidjaz Premium")
ev.append(f"Dialogue: 3,{ts(T0+0.45)},{ts(TOTAL)},Shape,,0,0,0,,{{\\pos(350,985)\\1c{GOLD}\\fad(400,350)\\p1}}m 0 0 l 380 0 l 380 4 l 0 4{{\\p0}}")
ev.append(f"Dialogue: 3,{ts(T0+0.65)},{ts(TOTAL)},Sub,,0,0,0,,{{\\pos(540,1060)\\fad(400,350)}}НАПИШИТЕ НАМ В {{\\c{GOLD}}}WHATSAPP")
ev.append(f"Dialogue: 5,{ts(TOTAL-0.45)},{ts(TOTAL)},Shape,,0,0,0,,{{\\pos(0,0)\\1c&H000000&\\alpha&HFF&\\t(0,450,\\alpha&H00&)\\p1}}m 0 0 l 1080 0 l 1080 1920 l 0 1920{{\\p0}}")
HDR = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter Black,84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,0,0,0,0,100,100,1,0,1,3,5,5,60,60,0,1
Style: Big,Inter Black,150,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,2,0,1,0,7,5,40,40,0,1
Style: Chip,Inter Black,52,&H00101010,&H00101010,&H003DC1F2,&H003DC1F2,0,0,0,0,100,100,3,0,3,14,0,5,0,0,0,1
Style: Brand,Cormorant Garamond SemiBold,156,&H003DC1F2,&H003DC1F2,&H00000000,&H96000000,0,0,0,0,100,100,3,0,1,0,4,5,0,0,0,1
Style: Sub,Inter Black,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,2,0,1,0,3,5,0,0,0,1
Style: Shape,Inter,20,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
open(f"{V2}/captions_V2.ass", "w").write(HDR + "\n".join(ev) + "\n")

# ---------- atmosphere ----------
atm = {"duration": TOTAL, "bed_db": -45, "events": [
    {"type": "impact", "t": 0.0, "db": -24},
    *[{"type": "whoosh", "t": round(s["a"] - 0.35, 2), "db": -34, "pan": (-0.3 if k % 2 else 0.3)}
      for k, s in enumerate(SHOTS) if s["type"] == "broll" and s["id"] not in ("s15",) and s["a"] > 0.5],
    {"type": "impact", "t": 26.10, "db": -30},
    {"type": "shimmer", "t": 26.15, "db": -33}]}
json.dump(atm, open(f"{V2}/atmos_spec.json", "w"), indent=1)
subprocess.run(["python3", "-I", f"{SCR}/atmos.py", f"{V2}/atmos_spec.json", f"{V2}/atmos.wav"], check=True)

# ---------- final mix + encode ----------
VOICE = ("highpass=f=70,equalizer=f=180:t=q:w=1.0:g=-1,equalizer=f=4200:t=q:w=1.4:g=1.2,"
         "deesser=i=0.15,acompressor=threshold=-26dB:ratio=2:attack=15:release=220:makeup=1.5")
OUT = f"{V2}/HP-001_VID-001_V2.mp4"
fc = (f"[0:v]subtitles={V2}/captions_V2.ass:fontsdir=/root/.fonts,format=yuv420p[v];"
      f"[1:a]{VOICE},aresample=48000,pan=stereo|c0=c0|c1=c0,apad=whole_dur={TOTAL}[vo];"
      f"[2:a]aresample=48000[am];"
      f"[vo][am]amix=inputs=2:normalize=0:duration=first,"
      f"LOUDNORM,alimiter=limit=0.85:level=false,atrim=end={TOTAL-0.02},afade=t=out:st={TOTAL-0.6}:d=0.55[a]")
# two-pass linear loudness normalisation (no dynamic pumping on the voice)
m = subprocess.run(["ffmpeg", "-hide_banner", "-i", f"{V2}/voice_raw.wav", "-i", f"{V2}/atmos.wav", "-filter_complex",
    f"[0:a]{VOICE},aresample=48000,pan=stereo|c0=c0|c1=c0,apad=whole_dur={TOTAL}[vo];[1:a]aresample=48000[am];[vo][am]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
    "-f", "null", "-"], capture_output=True, text=True).stderr
mj = json.loads(m[m.rindex("{"):m.rindex("}")+1])
LN = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={mj['input_i']}:measured_TP={mj['input_tp']}:measured_LRA={mj['input_lra']}:"
      f"measured_thresh={mj['input_thresh']}:offset={mj['target_offset']}:linear=true")
fc = fc.replace("LOUDNORM", LN)
open(f"{V2}/audio_chain_v2.txt", "w").write(VOICE + "\n" + LN + "\n")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{V2}/video_nocap.mp4", "-i", f"{V2}/voice_raw.wav", "-i", f"{V2}/atmos.wav",
    "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p", "-r", "30", "-g", "60",
    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-map_metadata", "-1", "-movflags", "+faststart", OUT], check=True)
json.dump({"shots": SHOTS, "pieces": place}, open(f"{V2}/edl_v2.json", "w"), ensure_ascii=False, indent=1)
print("done", OUT)

# HP-001 / VID-001 — V3 builder: improves V2 (same takes, same caption style) with meaning-led emotional scenes,
# clean studio packshots, no transition SFX, cleaner/denser voice, self-made ambient bed with soft ducking, unified grade.
import sys, os, json, subprocess, re
S = sys.argv[1]; SRC = f"{S}/src/source.mov"; V3 = f"{S}/v3"; SCR = f"{S}/scripts"; GEN = f"{V3}/gen_up"
FPS = 30; TOTAL = 30.70
P3 = {p["id"]: p for p in json.load(open(f"{V3}/voice_raw.wav.json"))["pieces"]}
CHOICE = json.load(open(f"{V3}/choice.json"))  # scene -> chosen upscaled image path (picked after visual review)

# ---- shot list (output seconds); "dis" = soft dissolve INTO this shot (seconds) ----
SHOTS = [
 dict(id="a01", a=0.00,  b=6.00,  type="spk", piece="H",   z=(1.12, 1.20)),                       # direct question, one continuous take
 dict(id="a02", a=6.00,  b=8.47,  type="img", scene="gift",    zoom=(1.08, 1.13), center=(0.42, 0.50)),  # care / tenderness
 dict(id="a03", a=8.47,  b=10.00, type="pack", items=[dict(src="leather", x=0.5, base=0.70, width=700)], floor=0.69, zoom=(1.0, 1.03)),  # reverence
 dict(id="a04", a=10.00, b=14.60, type="spk", piece="L3",  z=(1.10, 1.17)),                        # conviction: whole thought on one take
 dict(id="a05", a=14.60, b=19.40, type="img", scene="parents", zoom=(1.0, 1.07), center=(0.5, 0.36)),  # love, one strong frame (clean cut, no dissolve)
 dict(id="a06", a=19.40, b=21.75, type="spk", piece="L5a", z=(1.14, 1.19)),
 dict(id="a07", a=21.75, b=23.92, type="img", scene="dawn",    zoom=(1.0, 1.05), center=(0.45, 0.62)),   # the page, morning light, memory
 dict(id="a08", a=23.92, b=25.09, type="spk", piece="L6a", z=(1.08, 1.11)),
 dict(id="a09", a=25.09, b=TOTAL, type="pack", floor=0.585, zoom=(1.05, 1.0), items=[
        dict(src="ivory", x=0.27, base=0.60, width=400), dict(src="leather", x=0.73, base=0.60, width=400),
        dict(src="box", x=0.5, base=0.69, width=480)]),                                              # choice + brand
]
fr = lambda t: int(round(t*FPS))
for s in SHOTS: s["n"] = fr(s["b"]) - fr(s["a"])
assert sum(s["n"] for s in SHOTS) == fr(TOTAL)
# a shot that dissolves INTO the next one needs extra tail frames
for i, s in enumerate(SHOTS[:-1]):
    s["tail"] = fr(SHOTS[i+1].get("dis", 0))

# ---- render stills/packshots ----
spec = []
for s in SHOTS:
    n = s["n"] + s.get("tail", 0)
    if s["type"] == "img":
        spec.append(dict(id=s["id"], kind="img", src=CHOICE[s["scene"]], n=n, zoom=s["zoom"], center=s["center"]))
    elif s["type"] == "pack":
        spec.append(dict(id=s["id"], kind="packshot", n=n, items=s["items"], floor=s["floor"], zoom=s["zoom"]))
json.dump(spec, open(f"{V3}/shots_spec.json", "w"), indent=1)
if "--skip-shots" not in sys.argv:
    subprocess.run(["python3", "-I", f"{SCR}/shots_v3.py", f"{V3}/shots_spec.json", V3, V3], check=True)

# ---- speaker shots (same takes as V2) ----
TM = "zscale=t=linear:npl=203,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv:p=bt709,format=yuv420p"
FX, FY = 550, 1000
for s in SHOTS:
    if s["type"] != "spk": continue
    if "--skip-spk" in sys.argv and os.path.exists(f"{V3}/{s['id']}.mp4"): continue
    p = P3[s["piece"]]; src_t = p["src_in"] + (s["a"] - p["out_in"]); n = s["n"] + s.get("tail", 0); D = n/FPS
    z0, z1 = s["z"]; z = f"({z0}+({z1}-{z0})*(3*pow(min(t/{D:.3f},1),2)-2*pow(min(t/{D:.3f},1),3)))"
    vf = (f"fps={FPS},{TM},setpts=PTS-STARTPTS,"
          f"scale=w='2*trunc(1080*{z}/2)':h='2*trunc(1920*{z}/2)':eval=frame:flags=lanczos,"
          f"crop=1080:1920:x='min(max({FX}*iw/1080-540,0),iw-1080)':y='min(max({FY}*ih/1920-960,0),ih-1920)',setsar=1")
    s["src_t"] = round(src_t, 3)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{src_t:.3f}", "-i", SRC, "-an", "-vf", vf, "-frames:v", str(n),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p", f"{V3}/{s['id']}.mp4"], check=True)
    print("speaker", s["id"], src_t, flush=True)

# ---- per-shot look (small differences only) + one shared cinematic grade ----
LOOK = {"spk": "eq=contrast=1.05:brightness=-0.02:saturation=1.0,colorbalance=rs=0.02:bs=-0.03",
        "img": "eq=contrast=1.03:saturation=0.92,colorbalance=rs=0.025:gs=0.005:bs=-0.035:rh=0.02:bh=-0.02",
        "pack": "eq=contrast=1.0:saturation=1.0"}
GRADE = ("curves=m='0/0.02 0.25/0.21 0.5/0.5 0.78/0.80 1/0.95',"      # deep-not-crushed shadows, soft highlights
         "colorbalance=rs=0.015:bs=-0.01:rm=0.01:bm=-0.015:rh=0.01:bh=-0.02,vignette=angle=PI/5.2,noise=alls=2:allf=t")
inputs, chains = [], []
for i, s in enumerate(SHOTS):
    inputs += ["-i", f"{V3}/{s['id']}.mp4"]
    chains.append(f"[{i}:v]settb=1/{FPS},setpts=N/{FPS}/TB,{LOOK[s['type']]},format=yuv420p[c{i}]")
cur, tcur = "[c0]", (SHOTS[0]["n"] + SHOTS[0].get("tail", 0))/FPS
for i in range(1, len(SHOTS)):
    s = SHOTS[i]; d = s.get("dis", 0); out = f"[j{i}]"
    if d:
        chains.append(f"{cur}[c{i}]xfade=transition=fade:duration={d}:offset={tcur - d:.4f},settb=1/{FPS}{out}")
        tcur += (s["n"] + s.get("tail", 0))/FPS - d
    else:
        chains.append(f"{cur}[c{i}]concat=n=2:v=1:a=0,settb=1/{FPS}{out}")
        tcur += (s["n"] + s.get("tail", 0))/FPS
    cur = out

# ---- captions (V2 style kept; timings mapped from V2 words through source time) ----
w2 = json.load(open(f"{S}/v2/words_snapped.json"))
P2 = json.load(open(f"{S}/v2/voice_raw.wav.json"))["pieces"]
def v2_to_src(t):
    best = min(P2, key=lambda p: 0 if p["out_in"] - 0.02 <= t <= p["out_out"] + 0.02 else min(abs(t - p["out_in"]), abs(t - p["out_out"])))
    return best["src_in"] + (t - best["out_in"])
def src_to_v3(x):
    for p in P3.values():
        if p["src_in"] - 0.05 <= x <= p["src_out"] + 0.05: return p["out_in"] + (x - p["src_in"])
    raise ValueError(x)
ws = [dict(w=w["w"], s=src_to_v3(v2_to_src(w["s"])), e=src_to_v3(v2_to_src(w["e"]))) for w in w2]
json.dump(ws, open(f"{V3}/words_v3.json", "w"), ensure_ascii=False, indent=1)
CH = [
 (0, 2, "А ВЫ\\NКОГДА-НИБУДЬ", "КОГДА-НИБУДЬ"), (3, 3, "ЗАДУМЫВАЛИСЬ,", "ЗАДУМЫВАЛИСЬ,"),
 (4, 5, "КАКОЙ ПОДАРОК", "ПОДАРОК"), (6, 7, "ДЕЙСТВИТЕЛЬНО\\NПРИНЕСЁТ", "ДЕЙСТВИТЕЛЬНО"), (8, 8, "ПОЛЬЗУ", "ПОЛЬЗУ"),
 (9, 11, "ВАШЕМУ БЛИЗКОМУ\\NЧЕЛОВЕКУ?", "БЛИЗКОМУ"),
 (12, 12, "ПРЕДСТАВЬТЕ,", "ПРЕДСТАВЬТЕ,"), (13, 14, "ВЫ ДАРИТЕ", "ДАРИТЕ"), (15, 17, "НЕ ПРОСТО\\NКНИГУ,", "КНИГУ,"),
 (18, 20, "А СВЯЩЕННЫЙ\\NКОРАН.", "КОРАН."),
 (21, 21, "ПОДАРОК,", "ПОДАРОК,"), (22, 24, "К КОТОРОМУ\\NЧЕЛОВЕК", "ЧЕЛОВЕК"), (25, 26, "БУДЕТ\\NВОЗВРАЩАТЬСЯ", "ВОЗВРАЩАТЬСЯ"),
 (27, 29, "СНОВА\\NИ СНОВА.", "СНОВА"),
 (30, 31, "ДЛЯ РОДИТЕЛЕЙ,", "РОДИТЕЛЕЙ,"), (32, 33, "ДЛЯ ЛЮБИМЫХ,", "ЛЮБИМЫХ,"),
 (34, 35, "ДЛЯ САМЫХ", "САМЫХ"), (36, 37, "ДОРОГИХ ЛЮДЕЙ.", "ДОРОГИХ"),
 (38, 39, "ПОДАРИТЕ ТО,", "ПОДАРИТЕ"), (40, 42, "ЧТО БУДЕТ\\NНАПОМИНАТЬ", "НАПОМИНАТЬ"), (43, 44, "О ВАС", "ВАС"),
 (45, 46, "С КАЖДОЙ", "КАЖДОЙ"), (47, 48, "ПРОЧИТАННОЙ\\NСТРАНИЦЕЙ.", "СТРАНИЦЕЙ."),
 (49, 50, "НАПИШИТЕ НАМ", "НАПИШИТЕ"), (51, 52, "В WHATSAPP,", "WHATSAPP,"), (53, 55, "И МЫ\\NПОДБЕРЁМ", "ПОДБЕРЁМ"),
 (56, 57, "ДЛЯ ВАС", "ВАС"), (58, 59, "ПОДХОДЯЩИЙ\\NКОРАН.", "КОРАН."),
]
CAP_Y = json.load(open(f"{V3}/cap_y.json")) if os.path.exists(f"{V3}/cap_y.json") else {}
def shot_at(t): return next(s for s in SHOTS if s["a"] <= t < s["b"])
def ts(t):
    t = max(t, 0); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
GOLD = "&H3DC1F2&"
starts = [max(ws[a]["s"] - 0.06, 0) for a, *_ in CH]
END_SPEECH = ws[59]["e"] + 0.25
ev = []
for k, (a, b, text, hl) in enumerate(CH):
    st = starts[k]; en = starts[k+1] if k+1 < len(CH) else END_SPEECH
    y = CAP_Y.get(shot_at(st + 0.05)["id"], 1478)
    parts = []
    for tok in text.replace("\\N", " \\N ").split(" "):
        if tok == "\\N": parts.append("\\N"); continue
        parts.append(f"{{\\c{GOLD}}}{tok}{{\\c&HFFFFFF&}}" if tok == hl else tok)
    body = " ".join(parts).replace(" \\N ", "\\N")
    ev.append(f"Dialogue: 2,{ts(st)},{ts(en)},Cap,,0,0,0,,{{\\pos(540,{y})\\fscx94\\fscy94\\t(0,90,\\fscx100\\fscy100)}}{body}")
def chip(t0, t1, text, y=330):
    return f"Dialogue: 4,{ts(t0)},{ts(t1)},Chip,,0,0,0,,{{\\pos(540,{y})\\fad(120,120)}}{text}"
ev.append(chip(0.10, 2.60, "HIDJAZ PREMIUM"))
ev.append(chip(23.98, 25.05, "WHATSAPP"))
T0 = END_SPEECH + 0.10
ev.append(f"Dialogue: 3,{ts(T0)},{ts(TOTAL)},Brand,,0,0,0,,{{\\pos(540,440)\\fad(700,500)\\blur0.4}}Hidjaz Premium")
ev.append(f"Dialogue: 3,{ts(T0+0.30)},{ts(TOTAL)},Shape,,0,0,0,,{{\\pos(350,540)\\1c{GOLD}\\fad(600,500)\\p1}}m 0 0 l 380 0 l 380 4 l 0 4{{\\p0}}")
ev.append(f"Dialogue: 3,{ts(T0+0.50)},{ts(TOTAL)},Sub,,0,0,0,,{{\\pos(540,615)\\fad(600,500)}}НАПИШИТЕ НАМ В {{\\c{GOLD}}}WHATSAPP")
ev.append(f"Dialogue: 5,{ts(TOTAL-0.60)},{ts(TOTAL)},Shape,,0,0,0,,{{\\pos(0,0)\\1c&H000000&\\alpha&HFF&\\t(0,600,\\alpha&H00&)\\p1}}m 0 0 l 1080 0 l 1080 1920 l 0 1920{{\\p0}}")
HDR = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter Black,84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,3.2,5,5,60,60,0,1
Style: Chip,Inter Black,50,&H00101010,&H00101010,&H003DC1F2,&H003DC1F2,0,0,0,0,100,100,3,0,3,14,0,5,0,0,0,1
Style: Brand,Cormorant Garamond SemiBold,156,&H003DC1F2,&H003DC1F2,&H00000000,&H96000000,0,0,0,0,100,100,3,0,1,0,4,5,0,0,0,1
Style: Sub,Inter Black,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,2,0,1,0,3,5,0,0,0,1
Style: Shape,Inter,20,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
open(f"{V3}/captions_V3.ass", "w").write(HDR + "\n".join(ev) + "\n")
chains.append(f"{cur}{GRADE},subtitles={V3}/captions_V3.ass:fontsdir=/root/.fonts,trim=end_frame={fr(TOTAL)},format=yuv420p[v]")

# ---- ambient bed: louder in pauses, swell on emotional holds and finale ----
def ends(pid): return P3[pid]["out_out"]
keys = [[0, -21], [5.6, -21], [6.1, -19], [ends("L2b"), -19], [ends("L2b")+0.35, -16], [10.1, -19],
        [ends("L3"), -19], [ends("L3")+0.4, -15.5], [14.9, -19], [ends("L4"), -19], [ends("L4")+0.4, -15], [18.8, -19],
        [END_SPEECH, -19], [END_SPEECH+0.8, -13], [TOTAL-1.2, -13.5], [TOTAL, -40]]
json.dump({"duration": TOTAL, "keys": keys}, open(f"{V3}/pad_spec.json", "w"), indent=1)
subprocess.run(["python3", "-I", f"{SCR}/pad_v3.py", f"{V3}/pad_spec.json", f"{V3}/pad.wav"], check=True)

VOICE = ("highpass=f=80,afftdn=nr=10:nf=-60:tn=1,"
         "equalizer=f=160:t=q:w=0.9:g=2.2,equalizer=f=350:t=q:w=1.2:g=-1.6,equalizer=f=3300:t=q:w=1.3:g=1.4,"
         "equalizer=f=9000:t=q:w=1.0:g=-1.0,deesser=i=0.2,"
         "acompressor=threshold=-24dB:ratio=3:attack=8:release=160:knee=6:makeup=2")
AFILT = (f"[{len(SHOTS)}:a]{VOICE},aresample=48000,pan=stereo|c0=c0|c1=c0,apad=whole_dur={TOTAL},asplit=2[vo][sc];"
         f"[{len(SHOTS)+1}:a]aresample=48000[pad];"
         f"[pad][sc]sidechaincompress=threshold=0.025:ratio=2.5:attack=120:release=700:knee=6:makeup=1[padd];"
         f"[vo][padd]amix=inputs=2:normalize=0:duration=first,LOUDNORM,alimiter=limit=0.89:attack=5:release=60:level=false,"
         f"atrim=end={TOTAL-0.02}[a]")
def mix_cmd(af, out_args):
    return (["ffmpeg", "-hide_banner", "-y"] + inputs + ["-i", f"{V3}/voice_raw.wav", "-i", f"{V3}/pad.wav"]
            + ["-filter_complex", ";".join(chains) + ";" + af] + out_args)
m = subprocess.run(["ffmpeg", "-hide_banner", "-i", f"{V3}/voice_raw.wav", "-i", f"{V3}/pad.wav", "-filter_complex",
    AFILT.replace(f"[{len(SHOTS)}:a]", "[0:a]").replace(f"[{len(SHOTS)+1}:a]", "[1:a]").replace("LOUDNORM", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json").replace("[a]", ""),
    "-f", "null", "-"], capture_output=True, text=True).stderr
mj = json.loads(m[m.rindex("{"):m.rindex("}")+1])
LN = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={mj['input_i']}:measured_TP={mj['input_tp']}:measured_LRA={mj['input_lra']}:"
      f"measured_thresh={mj['input_thresh']}:offset={mj['target_offset']}:linear=true")
open(f"{V3}/audio_chain_v3.txt", "w").write(VOICE + "\n" + LN + "\n")
OUT = f"{V3}/HP-001_VID-001_V3_master.mp4"
r = subprocess.run(mix_cmd(AFILT.replace("LOUDNORM", LN), ["-map", "[v]", "-map", "[a]",
    "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p", "-r", "30", "-g", "60",
    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-map_metadata", "-1", "-movflags", "+faststart", OUT]), capture_output=True, text=True)
if r.returncode: print(r.stderr[-3000:]); sys.exit(1)
json.dump({"shots": SHOTS, "pieces": list(P3.values()), "choice": CHOICE}, open(f"{V3}/edl_v3.json", "w"), ensure_ascii=False, indent=1)
print("done", OUT)

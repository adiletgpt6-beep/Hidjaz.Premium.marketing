# HP-001 / VID-001 — V4 builder ("hidjaz.kuran" premium re-edit).
# Real Quran products composited into clean table plates, two reviewed emotional scenes, the same best takes,
# breath-cleaned voice, self-composed chord bed with soft ducking, restrained premium captions, minimal brand end.
import sys, os, json, subprocess, re
S = sys.argv[1]; SRC = f"{S}/src/source.mov"; V4 = f"{S}/v4"; SCR = f"{S}/scripts"
FPS = 30
CFG = json.load(open(f"{V4}/shots.json")); TOTAL = CFG["total"]; SHOTS = CFG["shots"]
P4 = {p["id"]: p for p in json.load(open(f"{V4}/voice_raw.wav.json"))["pieces"]}
fr = lambda t: int(round(t*FPS))
for s in SHOTS: s["n"] = fr(s["b"]) - fr(s["a"])
assert sum(s["n"] for s in SHOTS) == fr(TOTAL), (sum(s["n"] for s in SHOTS), fr(TOTAL))

# ---- stills: composited product shots and upscaled scenes, very slow camera move only ----
spec = [dict(id=s["id"], kind="img", src=s["still"], n=s["n"], zoom=s["zoom"], center=s["center"]) for s in SHOTS if s["type"] in ("comp", "img")]
json.dump(spec, open(f"{V4}/shots_spec.json", "w"), indent=1)
if "--skip-shots" not in sys.argv:
    subprocess.run(["python3", "-I", f"{SCR}/shots_v3.py", f"{V4}/shots_spec.json", V4, V4], check=True)

# ---- speaker shots (same takes as V2/V3; L5a now starts after the inhale) ----
TM = "zscale=t=linear:npl=203,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv:p=bt709,format=yuv420p"
FX, FY = 550, 1000
for s in SHOTS:
    if s["type"] != "spk": continue
    if "--skip-spk" in sys.argv and os.path.exists(f"{V4}/{s['id']}.mp4"): continue
    p = P4[s["piece"]]; src_t = p["src_in"] + (s["a"] - p["out_in"]); n = s["n"]; D = n/FPS
    z0, z1 = s["z"]; z = f"({z0}+({z1}-{z0})*(3*pow(min(t/{D:.3f},1),2)-2*pow(min(t/{D:.3f},1),3)))"
    vf = (f"fps={FPS},{TM},setpts=PTS-STARTPTS,"
          f"scale=w='2*trunc(1080*{z}/2)':h='2*trunc(1920*{z}/2)':eval=frame:flags=lanczos,"
          f"crop=1080:1920:x='min(max({FX}*iw/1080-540,0),iw-1080)':y='min(max({FY}*ih/1920-960,0),ih-1920)',setsar=1")
    s["src_t"] = round(src_t, 3)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{src_t:.3f}", "-i", SRC, "-an", "-vf", vf, "-frames:v", str(n),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p", f"{V4}/{s['id']}.mp4"], check=True)
    print("speaker", s["id"], src_t, flush=True)

# ---- one shared premium grade; per-type looks only nudge toward it ----
LOOK = {"spk": "eq=contrast=1.04:brightness=-0.025:saturation=0.97,colorbalance=rs=0.02:bs=-0.03",
        "img": "eq=contrast=1.02:saturation=0.90,colorbalance=rs=0.02:bs=-0.03:rh=0.015:bh=-0.02",
        "comp": "eq=contrast=1.03:saturation=0.95,colorbalance=rs=0.015:bs=-0.02"}
GRADE = ("curves=m='0/0.025 0.25/0.215 0.5/0.5 0.8/0.81 1/0.955',"
         "colorbalance=rs=0.012:bs=-0.012:rm=0.012:bm=-0.018:rh=0.012:bh=-0.022,vignette=angle=PI/5.4,noise=alls=2:allf=t")
inputs, chains = [], []
for i, s in enumerate(SHOTS):
    inputs += ["-i", f"{V4}/{s['id']}.mp4"]
    chains.append(f"[{i}:v]settb=1/{FPS},setpts=N/{FPS}/TB,{LOOK[s['type']]},format=yuv420p[c{i}]")
chains.append("".join(f"[c{i}]" for i in range(len(SHOTS))) + f"concat=n={len(SHOTS)}:v=1:a=0,settb=1/{FPS}[cat]")

# ---- captions: restrained, sentence case, highlight only a few key words ----
w2 = json.load(open(f"{S}/v2/words_snapped.json")); P2 = json.load(open(f"{S}/v2/voice_raw.wav.json"))["pieces"]
def v2_to_src(t):
    b = min(P2, key=lambda p: 0 if p["out_in"]-0.02 <= t <= p["out_out"]+0.02 else min(abs(t-p["out_in"]), abs(t-p["out_out"])))
    return b["src_in"] + (t - b["out_in"])
def src_to_v4(x):
    for p in P4.values():
        if p["src_in"]-0.05 <= x <= p["src_out"]+0.05: return p["out_in"] + (x - p["src_in"])
    # word onset that now falls before a trimmed piece start (L5a): snap to that piece start
    nxt = min((p for p in P4.values() if p["src_in"] > x), key=lambda p: p["src_in"]); return nxt["out_in"]
ws = [dict(w=w["w"], s=src_to_v4(v2_to_src(w["s"])), e=src_to_v4(v2_to_src(w["e"]))) for w in w2]
json.dump(ws, open(f"{V4}/words_v4.json", "w"), ensure_ascii=False, indent=1)
CH = CFG["captions"]
def ts(t):
    t = max(t, 0); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
GOLD = "&H6AB2D8&"   # #D8B26A soft gold
starts = [max(ws[a]["s"] - 0.05, 0) for a, *_ in CH]
END_SPEECH = ws[59]["e"] + 0.25
ev = []
for k, (a, b, text, hls) in enumerate(CH):
    st = starts[k]; en = starts[k+1] if k+1 < len(CH) else END_SPEECH
    body = text
    for h in hls: body = body.replace(h, f"{{\\c{GOLD}}}{h}{{\\c&HFFFFFF&}}", 1)
    ev.append(f"Dialogue: 2,{ts(st)},{ts(en)},Cap,,0,0,0,,{{\\pos(540,{CFG.get('cap_y', 1585)})}}{body}")
T0 = END_SPEECH + 0.15
B = CFG["brand"]
ev.append(f"Dialogue: 3,{ts(T0)},{ts(TOTAL)},Brand,,0,0,0,,{{\\pos(540,{B['y']})\\fad(900,600)}}hidjaz.kuran")
ev.append(f"Dialogue: 3,{ts(T0+0.35)},{ts(TOTAL)},Shape,,0,0,0,,{{\\pos(440,{B['y']+78})\\1c{GOLD}\\fad(700,600)\\p1}}m 0 0 l 200 0 l 200 2 l 0 2{{\\p0}}")
ev.append(f"Dialogue: 3,{ts(T0+0.55)},{ts(TOTAL)},Sub,,0,0,0,,{{\\pos(540,{B['y']+128})\\fad(700,600)}}Напишите нам в WhatsApp")
ev.append(f"Dialogue: 5,{ts(TOTAL-0.70)},{ts(TOTAL)},Shape,,0,0,0,,{{\\pos(0,0)\\1c&H000000&\\alpha&HFF&\\t(0,700,\\alpha&H00&)\\p1}}m 0 0 l 1080 0 l 1080 1920 l 0 1920{{\\p0}}")
HDR = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter SemiBold,60,&H00FFFFFF,&H00FFFFFF,&H8C000000,&H96000000,0,0,0,0,100,100,0.5,0,1,2.4,1.5,5,90,90,0,1
Style: Brand,Cormorant Garamond SemiBold,120,&H006AB2D8,&H006AB2D8,&H00000000,&H96000000,0,0,0,0,100,100,2,0,1,0,2,5,0,0,0,1
Style: Sub,Inter Medium,42,&H20FFFFFF,&H20FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,1,0,1,0,2,5,0,0,0,1
Style: Shape,Inter,20,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
open(f"{V4}/captions_V4.ass", "w").write(HDR + "\n".join(ev) + "\n")
chains.append(f"[cat]{GRADE},subtitles={V4}/captions_V4.ass:fontsdir=/root/.fonts,trim=end_frame={fr(TOTAL)},format=yuv420p[v]")

# ---- music bed: chord changes on emotional beats, louder in pauses, smooth ----
def oo(pid): return P4[pid]["out_out"]
def oi(pid): return P4[pid]["out_in"]
CHORDS = [[0.0, [38, 50, 57, 62, 65]],            # Dm
          [oi("L2a"), [34, 46, 53, 58, 62]],      # Bb  (the gift)
          [oi("L3"), [41, 53, 57, 60, 65]],       # F
          [oi("L4"), [36, 48, 55, 60, 64]],       # C   (parents)
          [oi("L5a"), [34, 46, 53, 58, 62]],      # Bb
          [oi("L6a"), [38, 50, 57, 62, 65]]]      # Dm  (finale)
keys = [[0, -19], [oo("H"), -19], [oo("H")+0.3, -14], [oi("L2a"), -19], [oo("L2b"), -19], [oo("L2b")+0.35, -13], [oi("L3"), -19.5],
        [oo("L3"), -19.5], [oo("L3")+0.35, -13], [oi("L4"), -19], [oo("L4"), -19], [oo("L4")+0.35, -12.5], [oi("L5a"), -19],
        [END_SPEECH, -19], [END_SPEECH+1.0, -11.5], [TOTAL-1.4, -12], [TOTAL, -40]]
json.dump({"duration": TOTAL, "chords": CHORDS, "keys": keys}, open(f"{V4}/pad_spec.json", "w"), indent=1)
subprocess.run(["python3", "-I", f"{SCR}/pad_v4.py", f"{V4}/pad_spec.json", f"{V4}/pad.wav"], check=True)

VOICE = ("highpass=f=80,adeclick=w=55:o=75,afftdn=nr=8:nf=-60:tn=1,"
         "equalizer=f=160:t=q:w=0.9:g=2.0,equalizer=f=350:t=q:w=1.2:g=-1.5,equalizer=f=3300:t=q:w=1.3:g=1.2,"
         "equalizer=f=9000:t=q:w=1.0:g=-1.0,deesser=i=0.18,"
         "acompressor=threshold=-24dB:ratio=2.6:attack=10:release=180:knee=6:makeup=2")
AF = (f"[{len(SHOTS)}:a]{VOICE},aresample=48000,pan=stereo|c0=c0|c1=c0,apad=whole_dur={TOTAL},asplit=2[vo][sc];"
      f"[{len(SHOTS)+1}:a]aresample=48000[pad];"
      f"[pad][sc]sidechaincompress=threshold=0.03:ratio=2.5:attack=200:release=900:knee=8:makeup=1[padd];"
      f"[vo][padd]amix=inputs=2:normalize=0:duration=first,LOUDNORM,alimiter=limit=0.89:attack=5:release=60:level=false,atrim=end={TOTAL-0.02}[a]")
probe = (AF.replace(f"[{len(SHOTS)}:a]", "[0:a]").replace(f"[{len(SHOTS)+1}:a]", "[1:a]")
         .replace("LOUDNORM", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json").replace("[a]", ""))
m = subprocess.run(["ffmpeg", "-hide_banner", "-i", f"{V4}/voice_raw.wav", "-i", f"{V4}/pad.wav", "-filter_complex", probe, "-f", "null", "-"],
                   capture_output=True, text=True).stderr
mj = json.loads(m[m.rindex("{"):m.rindex("}")+1])
GAIN = -14 - float(mj["input_i"])        # fixed linear gain (never dynamic)
LN = f"volume={GAIN:.2f}dB"
open(f"{V4}/audio_chain_v4.txt", "w").write(VOICE + "\n" + LN + "\n")
OUT = f"{V4}/HP-001_VID-001_V4_master.mp4"
r = subprocess.run(["ffmpeg", "-hide_banner", "-y"] + inputs + ["-i", f"{V4}/voice_raw.wav", "-i", f"{V4}/pad.wav",
    "-filter_complex", ";".join(chains) + ";" + AF.replace("LOUDNORM", LN), "-map", "[v]", "-map", "[a]",
    "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p", "-r", "30", "-g", "60",
    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-map_metadata", "-1", "-movflags", "+faststart", OUT], capture_output=True, text=True)
if r.returncode: print(r.stderr[-3000:]); sys.exit(1)
json.dump({"shots": SHOTS, "pieces": list(P4.values()), "gain_db": GAIN}, open(f"{V4}/edl_v4.json", "w"), ensure_ascii=False, indent=1)
print("done", OUT, "gain", round(GAIN, 2))

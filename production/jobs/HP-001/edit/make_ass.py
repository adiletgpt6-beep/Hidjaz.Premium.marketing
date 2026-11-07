# Build V1 dynamic Russian captions (ASS) from ASR word timings + reviewed text.
import json, sys, re
asr, meta, out = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]
# Reviewed caption text (normalised spelling: "Куран" pronunciation -> "Коран"). '|' = chunk break.
TEXT = ("А вы когда-нибудь | задумывались, | какой подарок | действительно принесёт пользу | вашему близкому человеку? | "
        "Представьте, | вы дарите | не просто книгу, | а священный Коран. | "
        "Подарок, | к которому человек | будет возвращаться | снова и снова. | "
        "Для родителей, | для любимых, | для самых | близких людей. | "
        "Подарите то, | что будет напоминать | о вас | с каждой | прочитанной страницей. | "
        "Напишите нам | в WhatsApp — | и мы подберём | для вас | подходящий Коран.")
chunks = [c.split() for c in TEXT.split("|")]
words = [w for s in asr["segments"] for w in s["words"]]
# ASR splits "когда-нибудь" into two tokens; merge tokens that start with '-'
merged = []
for w in words:
    if w["w"].strip().startswith("-") and merged:
        merged[-1]["w"] += w["w"].strip(); merged[-1]["e"] = w["e"]
    else:
        merged.append(dict(w))
flat = [w for c in chunks for w in c if w != "—"]
norm = lambda s: re.sub(r"[^\wё]", "", s.lower()).replace("ё", "е")
assert len(merged) == len(flat), (len(merged), len(flat), [m["w"] for m in merged])
for m, f in zip(merged, flat):
    a, b = norm(m["w"]), norm(f)
    if a != b: print("normalised:", m["w"].strip(), "->", f)
def ts(t):
    t = max(t, 0); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"
GOLD, WHITE = "&H6AB2D8&", "&HFFFFFF&"   # BGR: #D8B26A
hdr = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter SemiBold,74,&H00FFFFFF,&H00FFFFFF,&H64000000,&H8C000000,0,0,0,0,100,100,0,0,1,2.2,3,5,90,90,0,1
Style: Mark,Cormorant Garamond SemiBold,58,&H006AB2D8,&H006AB2D8,&H00000000,&H96000000,0,0,0,0,100,100,9,0,1,0,2,5,0,0,0,1
Style: Brand,Cormorant Garamond SemiBold,128,&H006AB2D8,&H006AB2D8,&H00000000,&H96000000,0,0,0,0,100,100,3,0,1,0,3,5,0,0,0,1
Style: Sub,Inter Medium,50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,1,0,1,0,2,5,0,0,0,1
Style: Shape,Inter,20,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
ev = []
CY = 600  # caption centre: over the curtain, above the speaker's head in all framings
i = 0
spans = []
for c in chunks:
    toks = [w for w in c if w != "—"]
    ws = merged[i:i + len(toks)]; i += len(toks)
    spans.append((c, ws))
speech_end = meta["speech_end"]
for k, (c, ws) in enumerate(spans):
    start = ws[0]["s"] - 0.06
    end = spans[k + 1][1][0]["s"] - 0.06 if k + 1 < len(spans) else min(ws[-1]["e"] + 0.35, speech_end)
    wi = 0; times = []
    for tok in c:
        if tok == "—": times.append(None); continue
        times.append(ws[wi]); wi += 1
    real = [t for t in times if t]
    for j, w in enumerate(real):
        s = start if j == 0 else w["s"] - 0.03
        e = (real[j + 1]["s"] - 0.03) if j + 1 < len(real) else end
        parts = []; rj = -1
        for tok, t in zip(c, times):
            if t: rj += 1
            col = GOLD if (t and rj == j) else WHITE
            parts.append(f"{{\\c{col}}}{tok}")
        pop = "{\\fscx92\\fscy92\\t(0,90,\\fscx100\\fscy100)}" if j == 0 else ""
        ev.append(f"Dialogue: 1,{ts(s)},{ts(e)},Cap,,0,0,0,,{{\\pos(540,{CY})}}{pop}" + " ".join(parts))
# Opening wordmark
ev.append("Dialogue: 2,0:00:00.00,0:00:02.60,Mark,,0,0,0,,{\\pos(540,250)\\fad(250,450)}HIDJAZ PREMIUM")
# End card over frozen final frame
T0 = speech_end + 0.05; T1 = speech_end + meta["end_hold"]
ev.append(f"Dialogue: 0,{ts(T0)},{ts(T1)},Shape,,0,0,0,,{{\\pos(0,0)\\1a&H48&\\fad(450,0)\\p1}}m 0 0 l 1080 0 l 1080 1920 l 0 1920{{\\p0}}")
ev.append(f"Dialogue: 2,{ts(T0+0.25)},{ts(T1)},Brand,,0,0,0,,{{\\pos(540,860)\\fad(450,0)\\blur0.6}}Hidjaz Premium")
ev.append(f"Dialogue: 2,{ts(T0+0.45)},{ts(T1)},Shape,,0,0,0,,{{\\pos(390,950)\\1c&H6AB2D8&\\fad(400,0)\\p1}}m 0 0 l 300 0 l 300 3 l 0 3{{\\p0}}")
ev.append(f"Dialogue: 2,{ts(T0+0.6)},{ts(T1)},Sub,,0,0,0,,{{\\pos(540,1030)\\fad(400,0)}}Напишите нам в WhatsApp")
open(out, "w").write(hdr + "\n".join(ev) + "\n")
print("events", len(ev))

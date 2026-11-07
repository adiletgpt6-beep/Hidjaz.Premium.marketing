# Assemble HP-001 V1 base edit (no captions) from source MOV.
import subprocess, sys, json
SRC, OUT = sys.argv[1], sys.argv[2]
# (src_in, src_out, framing, z_start, z_end)
SEGS = [
 (284.66, 286.00, "med",   1.28, 1.33),  # А вы когда-нибудь задумывались,
 (286.78, 290.95, "wide",  1.00, 1.04),  # какой подарок ... человеку?
 (305.64, 306.45, "close", 1.55, 1.60),  # Представьте, вы
 (307.22, 309.82, "wide",  1.05, 1.00),  # дарите не просто книгу, а священный Коран.
 (311.00, 315.00, "med",   1.30, 1.34),  # Подарок ... снова и снова.
 (316.55, 320.55, "close", 1.55, 1.60),  # Для родителей ... людей.
 (333.76, 339.05, "wide",  1.00, 1.04),  # Подарите то ... страницей.
 (339.98, 344.30, "med",   1.28, 1.36),  # Напишите нам в WhatsApp ... Коран.
]
END_HOLD = 2.8  # freeze of last frame for brand end card
FX, FY = 550, 1000  # speaker face centre in source (1080x1920 after rotation)
TONEMAP = "zscale=t=linear:npl=203,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv:p=bt709,format=yuv420p"
GRADE = "eq=contrast=1.04:saturation=1.06:gamma=1.01,vignette=angle=PI/6"
args = ["ffmpeg", "-v", "error", "-y"]
fc = []
for i, (a, b, fr, z0, z1) in enumerate(SEGS):
    d = b - a
    args += ["-ss", f"{a:.3f}", "-t", f"{d:.3f}", "-i", SRC]
    hold = END_HOLD if i == len(SEGS) - 1 else 0
    D = d + hold
    z = f"({z0}+({z1}-{z0})*min(t/{D:.3f},1))"
    cx, cy = (540, 960) if fr == "wide" else (FX, FY)
    pad = f",tpad=stop_mode=clone:stop_duration={hold}" if hold else ""
    fc.append(
        f"[{i}:v]fps=30,{TONEMAP}{pad},setpts=PTS-STARTPTS,"
        f"scale=w='2*trunc(1080*{z}/2)':h='2*trunc(1920*{z}/2)':eval=frame:flags=lanczos,"
        f"crop=1080:1920:x='min(max({cx}*iw/1080-540,0),iw-1080)':y='min(max({cy}*ih/1920-960,0),ih-1920)',"
        f"setsar=1,{GRADE}[v{i}]")
    apad = f",apad=pad_dur={hold}" if hold else ""
    fc.append(f"[{i}:a]aresample=48000,asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={d-0.03:.3f}:d=0.03{apad}[a{i}]")
n = len(SEGS)
fc.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
args += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p", "-r", "30",
         "-c:a", "pcm_s16le", "-map_metadata", "-1", OUT]
subprocess.run(args, check=True)
cuts, t = [], 0.0
for a, b, *_ in SEGS:
    t += b - a; cuts.append(round(t, 3))
json.dump({"segments": SEGS, "cut_points_out": cuts[:-1], "speech_end": cuts[-1], "end_hold": END_HOLD}, open(OUT + ".json", "w"), indent=1)
print("ok", cuts)

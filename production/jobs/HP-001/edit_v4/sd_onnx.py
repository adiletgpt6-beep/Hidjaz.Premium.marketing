# Minimal Stable Diffusion 1.5 text-to-image on ONNX Runtime + NumPy (CPU, no PyTorch).
# Model: Heliosoph/realistic-vision-cfg-onnx (Realistic Vision V6.0 B1 + sd-vae-ft-mse), CreativeML OpenRAIL-M.
# Sampler: Euler with Karras sigmas, classifier-free guidance.
import sys, json, time, numpy as np, onnxruntime as ort
from transformers import CLIPTokenizer
from PIL import Image
MODEL, OUT, SCENES_JSON = sys.argv[1], sys.argv[2], sys.argv[3]
which = sys.argv[4].split(",") if len(sys.argv) > 4 and sys.argv[4] else None
seeds = [int(x) for x in sys.argv[5].split(",")] if len(sys.argv) > 5 else [11, 22, 33]
STEPS = int(sys.argv[6]) if len(sys.argv) > 6 else 26
W_, H_ = 512, 896; CFG = 6.5
so = ort.SessionOptions(); so.intra_op_num_threads = 4; so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
so.enable_cpu_mem_arena = False; so.enable_mem_pattern = False
P = ["CPUExecutionProvider"]
tok = CLIPTokenizer.from_pretrained(f"{MODEL}/tokenizer")
te = ort.InferenceSession(f"{MODEL}/text_encoder/model.onnx", so, providers=P)
def embed(text):
    ids = tok(text, padding="max_length", max_length=77, truncation=True, return_tensors="np").input_ids.astype(np.int32)
    name = te.get_inputs()[0].name
    if "int64" in te.get_inputs()[0].type: ids = ids.astype(np.int64)
    return te.run(None, {name: ids})[0].astype(np.float32)
# schedule (scaled_linear, as SD1.5)
betas = np.linspace(0.00085**0.5, 0.012**0.5, 1000, dtype=np.float64)**2
ac = np.cumprod(1 - betas); sig_all = np.sqrt((1 - ac)/ac); log_sig = np.log(sig_all)
def karras(n, smin=sig_all[0], smax=sig_all[-1], rho=7.0):
    r = np.linspace(0, 1, n); mi, ma = smin**(1/rho), smax**(1/rho)
    return (ma + r*(mi - ma))**rho
def sigma_to_t(s):
    ls = np.log(s); idx = np.clip(np.searchsorted(log_sig, ls) - 1, 0, 998)
    lo, hi = log_sig[idx], log_sig[idx+1]; w = np.clip((lo - ls)/(lo - hi), 0, 1)
    return (1 - w)*idx + w*(idx+1)
scenes = json.load(open(SCENES_JSON)); NEG = scenes.pop("_negative")
neg_e = embed(NEG); log = []
EMB = {k: embed(v) for k, v in scenes.items() if not which or k in which}
del te; import gc; gc.collect()
un = ort.InferenceSession(f"{MODEL}/unet/model.onnx", so, providers=P)
vd = ort.InferenceSession(f"{MODEL}/vae_decoder/model.onnx", so, providers=P)
u_in = {i.name: i for i in un.get_inputs()}
t_name = [n for n in u_in if "time" in n][0]; t_type = u_in[t_name].type
x_name = [n for n in u_in if "sample" in n][0]; h_name = [n for n in u_in if "hidden" in n or "encoder" in n][0]
for name, prompt in scenes.items():
    if which and name not in which: continue
    cond = np.concatenate([neg_e, EMB[name]], 0)
    for sd in seeds:
        t0 = time.time(); rng = np.random.default_rng(sd)
        sig = np.append(karras(STEPS), 0.0)
        x = rng.standard_normal((1, 4, H_//8, W_//8)).astype(np.float32)*sig[0]
        for i in range(STEPS):
            s = sig[i]; t = sigma_to_t(s)
            xin = (x/np.sqrt(s*s + 1)).astype(np.float32)
            tt = np.array([t], dtype=np.float32) if "float" in t_type else np.array([int(round(t))], dtype=np.int64)
            if "float16" in t_type: tt = tt.astype(np.float16)
            tsc = tt.reshape(()) if len(u_in[t_name].shape) == 0 else np.repeat(tt, 2)
            eps = un.run(None, {x_name: np.concatenate([xin, xin], 0), t_name: tsc, h_name: cond})[0]
            e = eps[0:1] + CFG*(eps[1:2] - eps[0:1])
            den = x - s*e
            x = x + (x - den)/s*(sig[i+1] - s)
        img = vd.run(None, {vd.get_inputs()[0].name: (x/0.18215).astype(np.float32)})[0][0]
        img = ((np.clip(img, -1, 1) + 1)*127.5).round().astype(np.uint8).transpose(1, 2, 0)
        fn = f"{OUT}/{name}_{sd}.png"; Image.fromarray(img).save(fn)
        log.append({"scene": name, "seed": sd, "steps": STEPS, "cfg": CFG, "sec": round(time.time()-t0, 1), "file": fn})
        print(log[-1], flush=True)
json.dump({"model": "Heliosoph/realistic-vision-cfg-onnx (Realistic Vision V6.0 B1 + sd-vae-ft-mse)", "size": f"{W_}x{H_}",
           "negative": NEG, "runs": log}, open(f"{OUT}/genlog_{int(time.time())}.json", "w"), ensure_ascii=False, indent=1)

# Real-ESRGAN (realesr-general-x4v3, BSD-3) x4 super-resolution on ONNX Runtime, tiled; used ONLY on generated scenes/plates.
import sys, time, numpy as np, onnxruntime as ort
from PIL import Image
M, SRC, DST = sys.argv[1:4]
so = ort.SessionOptions(); so.intra_op_num_threads = 4
s = ort.InferenceSession(M, so, providers=["CPUExecutionProvider"]); inp = s.get_inputs()[0]
img = np.asarray(Image.open(SRC).convert("RGB")).astype(np.float32)/255
H, W = img.shape[:2]; T, PAD = 256, 16; out = np.zeros((H*4, W*4, 3), np.float32); t0 = time.time()
for y in range(0, H, T):
    for x in range(0, W, T):
        y0, x0 = max(y-PAD, 0), max(x-PAD, 0); y1, x1 = min(y+T+PAD, H), min(x+T+PAD, W)
        tile = img[y0:y1, x0:x1].transpose(2, 0, 1)[None]
        r = s.run(None, {inp.name: tile.astype(np.float32)})[0][0].transpose(1, 2, 0)
        oy, ox = (y-y0)*4, (x-x0)*4; h, w = min(T, H-y)*4, min(T, W-x)*4
        out[y*4:y*4+h, x*4:x*4+w] = r[oy:oy+h, ox:ox+w]
Image.fromarray((np.clip(out, 0, 1)*255+0.5).astype(np.uint8)).save(DST)
print("upscaled", SRC.split("/")[-1], f"{W}x{H} -> {W*4}x{H*4}", round(time.time()-t0, 1), "s")

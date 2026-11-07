# HP-001 / Studio VID-001 — STATUS

Status: **V1 edit rendered and QA-verified. R2 upload of the edited MP4 is still open** (this session had no R2 write access).
Style version: V1 (unchanged). GitHub Issue: #1. No new Studio ID was created and no re-upload was requested.

## Source (verified 2026-11-07)
- Studio VID-001, upload ID `aeaace7f-4d16-4ffd-ad76-6717f5c5a83f`, R2 key `live/raw/aeaace7f-4d16-4ffd-ad76-6717f5c5a83f/source.mov` (original untouched).
- Fetched with the Studio broker: `node studio-fetch.mjs adiletgpt6-beep/Hidjaz.Premium.marketing VID-001 ./source.mov` (needs `STUDIO_SOURCE_TOKEN`).
- Size 582355656 bytes. SHA-256 `6c00df5c317d6ac5b13420a5b8c91dc00f3f11c69a58408f86cc493badee10c2`: **matches**.
- ffprobe: iPhone 16 Pro, HEVC Main 10, 1920x1080 stored with -90° rotation (so the image is 1080x1920 vertical), HLG/BT.2020 HDR, about 60 fps (VFR), 349.49 s. AAC-LC mono 48 kHz. The file also carries Apple metadata tracks, including GPS location.

## Footage review
- One static vertical shot. The speaker sits at a desk against a burgundy curtain. Products on the desk: an ivory carved-cover Quran, a carved brown leather Quran, and a terracotta box with blue stones. A framed calligraphy panel stands on an easel.
- The speech is Russian (one short aside between takes). The recording holds about 6 takes of the same script, with long pauses and off-camera moments; in several takes the speaker reads with eyes down.
- Spoken script (final take): «А вы когда-нибудь задумывались, какой подарок действительно принесёт пользу вашему близкому человеку? Представьте, вы дарите не просто книгу, а священный Коран. Подарок, к которому человек будет возвращаться снова и снова. Для родителей, для любимых, для самых близких людей. Подарите то, что будет напоминать о вас с каждой прочитанной страницей. Напишите нам в WhatsApp, и мы подберём для вас подходящий Коран.»
- The speaker pronounces it «Куран»; captions use the standard spelling «Коран». No prices, features or promises beyond the speech were added.

## Edit decisions (V1)
- Take selection: the hook is the 284.7–290.9 s take; the rest comes from the final take (305.6–344.3 s), where the speaker keeps eye contact the whole time. An aborted start («Подарите то, что будет на…», 330.5 s) was skipped in favour of the full restart at 333.8 s. The 1 s pause after «Представьте, вы» was tightened.
- 8 segments, cuts at 1.34 / 5.51 / 6.32 / 8.92 / 12.92 / 16.92 / 22.21 / 26.53 s (output timeline). Every cut changes framing (wide 1.0× / medium ~1.3× / close ~1.6×, each with a slow 3–5% push), so the jump cuts read as motivated. No flashy transitions. 20–30 ms audio fades at each joint.
- Visual treatment, "Bordeaux & Gold":
  - HLG→SDR BT.709 tone-map (hable) with light contrast/saturation and a soft vignette.
  - Small gold "HIDJAZ PREMIUM" wordmark in Cormorant Garamond for the first 2.6 s.
  - Dynamic Russian captions in Inter SemiBold over the curtain (y≈600, clear of face and products), with the current word highlighted gold.
  - 2.8 s end card: darkened hold of the last frame, gold "Hidjaz Premium" with a hairline rule, and «Напишите нам в WhatsApp» (spoken CTA only, no invented contact data).
- Audio: high-pass 75 Hz, light FFT denoise, gentle EQ, de-esser, 2.5:1 compression, two-pass loudnorm with a limiter. No music (none requested or licensed).
- Privacy: all source metadata, including GPS, is stripped from the output (`-map_metadata -1`).
- Tools: FFmpeg 6.1, local faster-whisper large-v3 for transcription and caption timing. An OpenAI transcription call was attempted through the connected key and returned `insufficient_quota`, so no paid service was used.
- Reproducible: `production/jobs/HP-001/edit/` holds `build_base.py` (segments and framing), `make_ass.py` and `captions_V1.ass`, `audio_chain.txt` and the ASR transcript.

## Output
- File: `HP-001_VID-001_V1.mp4`, 30565565 bytes, SHA-256 `23bb46d66a8a2ca09f3e665aad46d45b8f52936ba15c6f5a27f78693ccdcf0ed`.
- H.264 High@4.2, yuv420p, BT.709, 1080x1920, 30/1 fps CFR, 883 frames, 29.433 s. AAC-LC stereo 48 kHz 192 kb/s, 29.400 s. `+faststart` (moov before mdat).
- Delivered to the owner as a file in the Claude Code session (session 01VBHhTsBFZ8xQ46aystzqgJ). **Not yet in R2.**

## QA (performed on the final file)
- Full decode with `ffmpeg -v error -f null`: no errors.
- blackdetect (0.1 s, pix_th 0.10): no black frames. freezedetect: no unintended freezes (the end card keeps a slow push).
- Video and audio both start at 0.000. Audio ends 33 ms before video, inside the silent end card. Video and audio come from the same source trims, so lip sync is preserved at every cut.
- Loudness: −15.2 LUFS integrated, LRA 1.9 LU, peak −4.3 dBFS.
- Speech check: local ASR on the edited timeline reproduces the full script in order with no stray fragments or doubled words. Caption text was reviewed against it; only spelling was normalised: «Куран»→«Коран», «страницы»→«страницей» (two ASR passes on the raw clip read «страницей»).
- Visual frame check at 8 points plus the end card: captions are legible, stay inside safe margins and never cover the face or products. Product appearance is unaltered apart from the global grade.
- Not done: a human listen-through on a phone. Recommended before publishing, especially to confirm «страницей» and «Коран» by ear.

## Next action
1. Upload `HP-001_VID-001_V1.mp4` to R2, for example `live/edited/aeaace7f-4d16-4ffd-ad76-6717f5c5a83f/HP-001_V1.mp4`. Use Studio or a session that has R2 write credentials. Verify the SHA-256 above after upload and record the key here.
2. Owner review of V1. Feedback goes into V1.1 or V2 under the same HP-001 ID.
3. Keep the original MOV in R2 unchanged.

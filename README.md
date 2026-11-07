# Hidjaz Premium — video production

## Workflow
1. Upload source MP4/MOV (up to 1 GB) through BalaGo Studio, selecting this repository.
2. Studio stores source in Cloudflare R2 and creates a GitHub Issue with source ID, secure broker reference, filename, size and SHA-256 where available. Never store video binaries, tokens or signed download URLs in git.
3. Assign job ID HP-001, HP-002 etc. Reuse an existing ID for retries; never create duplicate jobs.
4. Claude Code reads this README, production/STYLE_GUIDE.md and the job Issue; obtains the source through authorized Studio broker, verifies checksum and records progress.
5. Edit with FFmpeg/Remotion as appropriate. Preview, listen, verify audio/video, render H.264/AAC MP4, and deliver via R2 or approved artifact storage. GitHub holds metadata, reports, checkpoints, and links, not large MP4.
6. If access is blocked, document the exact blocker; do not claim a completed video. Do not run paid APIs without explicit approval.

## Default edit style V1
Premium Quran product marketing, clean fast pacing without jarring cuts; retain truthful product appearance and spoken meaning. Kyrgyz/Russian dynamic readable captions, careful speech cleanup, balanced sound. Background music only if explicitly requested and rights cleared. 1080x1920 30fps by default when vertical source; preserve source orientation unless job specifies otherwise. Every video should have a distinct visual treatment within the brand.
Style is versioned per job (V1, V2...), and later updates must not silently change existing jobs.

## Production records
For each job save production/jobs/HP-XXX/STATUS.md with source reference (not expiring URL), style version, decisions, render and QA status, output location and next action. Keep production/HANDOFF.md current. Never claim an unverified result.

## Studio integration
Existing Studio must be configured to allow this repository for the connected GitHub account. Check repo selection and issue creation before uploading a large file. Verify R2/broker retrieval end-to-end with a small test first.

## Mandatory MOV to MP4 output
Accept MOV and MP4 sources. When the input is MOV, preserve the original MOV in R2 and produce the final edited deliverable as .mp4 (H.264 video + AAC audio, yuv420p, faststart). Never simply rename the extension. Verify streams, duration, sync and playability with ffprobe/ffmpeg. Apply the same MP4 output requirement to other accepted source formats. Do not transcode the entire raw source unnecessarily; render the edited timeline directly to MP4.


## Mandatory Studio delivery
For every video processed via BalaGo Studio, Claude Code MUST read and follow [production/DELIVERY_RULES.md](production/DELIVERY_RULES.md). A job is not complete until verified MP4 playback and direct-download links are delivered and recorded. If secure delivery endpoints are missing, report this blocker; do not invent links.

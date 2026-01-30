# YouTube Captions → Transcript (MVP)

This project downloads **YouTube public captions only** (no ASR/Whisper) and converts them into a `transcript.txt` file. It processes a queue (`pool.txt`) sequentially, logging each run as JSONL, and uses atomic file writes and backups suitable for OneDrive sync.

## Project structure (under ROOT)

```
ROOT
  01_pool
    pool.txt
    pool.backup
  02_output
    youtube
  03_logs
    run.log.jsonl
  04_runtime
    tmp
  05_src
    main.py
    requirements.txt
    README.md
    src
      pool_io.py
      ytdlp_client.py
      captions_select.py
      vtt_parser.py
      logging_jsonl.py
      errors.py
```

## Setup (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install yt-dlp
```

`yt-dlp` must be on `PATH` (the pip install above covers this).

## Pool file format

`ROOT\01_pool\pool.txt` is **TSV** with a `.txt` extension. The first line is the header. Minimum required columns are enforced and any extra columns are preserved.

Required header:

```
url	sub_type	estado	idioma	attempts	last_error	video_id	titulo	output_folder	processed_at
```

## How to run

```powershell
python main.py
```

Optional overrides:

```powershell
python main.py --pool <path> --out <path> --log <path> --max-attempts 5
```

## Troubleshooting

- **NO_CAPTIONS**: The video has no subtitles or auto-captions available. This is final.
- **HTTP 429 / rate limit**: The script will retry with backoff; consider waiting and re-running.
- **Invalid URL**: Only `youtube.com` or `youtu.be` URLs are supported.

## OneDrive safety notes

Before each update to `pool.txt`, a timestamped backup is created under `01_pool\pool.backup`. Updates are written to a temporary file (`04_runtime\tmp\pool.tmp`) and then atomically replaced.

# NAS-Streamliner Architecture

## Operating model

- The watcher and classifier run on one host.
- The NAS storage destination can be a local path, mapped drive, or UNC path.
- `config/settings.yaml` is the single entry point for all runtime paths.
- The camera map file is referenced from `settings.yaml`.
- File readiness is determined by polling, not by filesystem events.
- A file is processed only after repeated scans show the same size and mtime.

## Runtime roots

```text
Inbound      Incoming uploads, usually from FTP or a synced share
Storage      Final archive path on the NAS
Quarantine   Files that cannot be safely classified
Logs         Local application logs
State        Local SQLite state and manifest JSONL
```

Recommended split:

- `Inbound`, `Logs`, `State`: local or always-mounted path
- `Storage`, `Quarantine`: NAS path

This avoids losing logs or state if the NAS share is temporarily unavailable.

## Final storage layout

```text
Storage/
  YYYY-MM-DD/
    FX3-001/
      Original/
        20260306_184512_FX3-001_FX3_C0012.mp4
      Proxy/
        20260306_184512_FX3-001_FX3_C0012__proxy_720p_cfr.mp4
```

If classification fails, the file moves to:

```text
Quarantine/
  YYYY-MM-DD/
    ffprobe-failed/
      20260306_184700_ffprobe-failed_clip-001.mov
```

## File naming policy

Original media is standardized as:

```text
YYYYMMDD_HHMMSS_<BODY_ID>_<SANITIZED_SOURCE_STEM>.<ext>
```

Examples:

```text
20260306_184512_FX3-001_FX3_C0012.mp4
20260306_184512_FX3-001_FX3_C0012__v02.mp4
```

Rules:

- Invalid path characters are replaced with `_`
- Repeated separators are collapsed
- Duplicate files get `__v02`, `__v03`, and so on
- Unknown capture dates fall back to `unknown-date_<BODY_ID>_<SOURCE_STEM>`

## Metadata priority

Capture date:

1. `creation_time`
2. Apple QuickTime creation date tags
3. File modified time if enabled
4. Quarantine or `unknown_date_folder`

Camera folder / body ID:

1. Serial number match
2. Model match
3. `unknown_camera_alias`

Recommended rule:

- Treat `alias` in `cam_map.yaml` as a stable physical body ID
- Good: `FX3-001`, `FX3-002`, `IPHONE-001`
- Avoid using editorial roles like `A-CAM`, `B-CAM` as the folder key

## NAS path model

The project now supports environment-variable path overrides in `settings.yaml`.

Example:

```text
${NAS_STREAMLINER_STORAGE_ROOT:-../runtime/storage}
```

That means:

- Use `NAS_STREAMLINER_STORAGE_ROOT` if it is set
- Otherwise use `../runtime/storage`

This is useful when the same repository must run in local development and on a NAS-attached workstation.

## Preflight validation

Before the watcher or classifier runs, preflight validation checks:

- camera map file exists
- inbound directory exists
- storage directory is writable
- quarantine directory is writable
- log directory is writable
- state directory is writable

Validation can be run without starting the watcher:

```powershell
python watcher.py --config config/settings.yaml --validate-only
```

## Module responsibilities

- `watcher.py`: watcher CLI entry point
- `classifier.py`: manual classification CLI entry point
- `encoder.py`: manual proxy encode CLI entry point
- `process_media.py`: classify + proxy encode CLI entry point
- `src/nas_streamliner/services/watcher.py`: polling scan and stable file selection
- `src/nas_streamliner/services/classifier.py`: metadata extraction, mapping, naming, and file move
- `src/nas_streamliner/services/encoder.py`: proxy encode and proxy path allocation
- `src/nas_streamliner/preflight.py`: NAS path and writability validation
- `src/nas_streamliner/state_store.py`: SQLite tracking for observed files
- `src/nas_streamliner/ffprobe.py`: `ffprobe` metadata extraction
- `src/nas_streamliner/naming.py`: standardized filename allocation and duplicate policy
- `src/nas_streamliner/filesystem.py`: same-volume move or copy-verify-replace for cross-volume destinations

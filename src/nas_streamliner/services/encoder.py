from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from ..config import Settings
from ..ffprobe import FFprobeError, probe_video_stream_summary
from ..manifest import ManifestWriter
from ..models import ProxyEncodeResult


class ProxyEncodeError(RuntimeError):
    pass


class ProxyEncoder:
    def __init__(self, settings: Settings, logger: logging.Logger | None = None) -> None:
        self.settings = settings
        self.logger = logger or logging.getLogger("nas_streamliner")
        self.manifest = ManifestWriter(settings.paths.manifest_path)

    def encode(self, source_path: str | Path) -> ProxyEncodeResult:
        if not self.settings.encoder.enabled:
            raise ProxyEncodeError("Encoder is disabled in settings.")

        resolved_path = Path(source_path).resolve()
        stream_summary = probe_video_stream_summary(resolved_path, self.settings.ffprobe)
        if stream_summary.width is None or stream_summary.height is None:
            raise ProxyEncodeError(f"No video stream found in {resolved_path}")

        destination_path = build_proxy_output_path(
            source_path=resolved_path,
            proxy_subdir_name=self.settings.encoder.proxy_subdir_name,
            proxy_suffix=self.settings.encoder.proxy_suffix,
            output_extension=self.settings.encoder.output_extension,
        )

        if (
            self.settings.encoder.skip_if_source_not_newer
            and destination_path.exists()
            and destination_path.stat().st_mtime >= resolved_path.stat().st_mtime
        ):
            result = ProxyEncodeResult(
                status="skipped",
                source_path=resolved_path,
                destination_path=destination_path,
                width=stream_summary.width,
                height=stream_summary.height,
                avg_frame_rate=stream_summary.avg_frame_rate,
            )
            self._write_manifest(result)
            self.logger.info("Skipped proxy encode for %s; up-to-date output exists.", resolved_path.name)
            return result

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_output = destination_path.with_name(f"{destination_path.stem}.encoding{destination_path.suffix}")
        if temporary_output.exists():
            temporary_output.unlink()

        command = self._build_ffmpeg_command(
            source_path=resolved_path,
            destination_path=temporary_output,
            avg_frame_rate=stream_summary.avg_frame_rate,
            has_audio=stream_summary.has_audio,
        )

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.settings.encoder.timeout_seconds or None,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ProxyEncodeError(
                f"ffmpeg binary not found: {self.settings.encoder.ffmpeg_binary}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ProxyEncodeError(
                f"ffmpeg timed out after {self.settings.encoder.timeout_seconds}s"
            ) from exc

        if completed.returncode != 0:
            if temporary_output.exists():
                temporary_output.unlink()
            raise ProxyEncodeError(completed.stderr.strip() or "ffmpeg encode failed")

        if not temporary_output.exists():
            raise ProxyEncodeError(f"ffmpeg completed without creating output: {temporary_output}")

        if destination_path.exists():
            destination_path.unlink()
        temporary_output.replace(destination_path)

        result = ProxyEncodeResult(
            status="encoded",
            source_path=resolved_path,
            destination_path=destination_path,
            width=stream_summary.width,
            height=stream_summary.height,
            avg_frame_rate=stream_summary.avg_frame_rate,
        )
        self._write_manifest(result)
        self.logger.info("Encoded proxy %s -> %s", resolved_path.name, destination_path)
        return result

    def _build_ffmpeg_command(
        self,
        source_path: Path,
        destination_path: Path,
        avg_frame_rate: str | None,
        has_audio: bool,
    ) -> list[str]:
        encoder_settings = self.settings.encoder
        command = [
            encoder_settings.ffmpeg_binary,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source_path),
            "-map",
            "0:v:0",
            "-vf",
            (
                f"scale=w='min(iw,{encoder_settings.max_width})':"
                f"h='min(ih,{encoder_settings.max_height})':"
                "force_original_aspect_ratio=decrease:force_divisible_by=2"
            ),
            "-c:v",
            encoder_settings.video_codec,
            "-preset",
            encoder_settings.video_preset,
            "-crf",
            str(encoder_settings.video_crf),
            "-pix_fmt",
            encoder_settings.pixel_format,
            "-fps_mode",
            "cfr",
        ]
        if avg_frame_rate and avg_frame_rate != "0/0":
            command.extend(["-r", avg_frame_rate])

        if has_audio:
            command.extend(
                [
                    "-map",
                    "0:a:0?",
                    "-c:a",
                    encoder_settings.audio_codec,
                    "-b:a",
                    encoder_settings.audio_bitrate,
                    "-metadata:s:a:0",
                    "title=Original Audio",
                ]
            )
        else:
            command.append("-an")

        if encoder_settings.movflags_faststart:
            command.extend(["-movflags", "+faststart"])

        command.append(str(destination_path))
        return command

    def _write_manifest(self, result: ProxyEncodeResult) -> None:
        payload = result.to_record()
        payload["event"] = "proxy_encode"
        self.manifest.write_record(payload)


def build_proxy_output_path(
    source_path: str | Path,
    proxy_subdir_name: str,
    proxy_suffix: str,
    output_extension: str,
) -> Path:
    resolved_path = Path(source_path).resolve()
    if resolved_path.parent.name.casefold() == "original":
        proxy_root = resolved_path.parent.parent / proxy_subdir_name
    else:
        proxy_root = resolved_path.parent / proxy_subdir_name

    normalized_extension = output_extension if output_extension.startswith(".") else f".{output_extension}"
    return proxy_root / f"{resolved_path.stem}{proxy_suffix}{normalized_extension.lower()}"

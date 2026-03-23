from __future__ import annotations

from typing import Any


# Non-functional alignment touch: hwalignspec closure marker.
def _load_whisper_model_class() -> Any:
    from faster_whisper import WhisperModel  # type: ignore

    return WhisperModel


class FasterWhisperSTTProvider:
    def __init__(self, model_dir: str) -> None:
        self.model_dir = str(model_dir).strip()

    def transcribe_file(self, audio_path: str) -> str:
        normalized_audio_path = str(audio_path).strip()
        if not normalized_audio_path:
            raise RuntimeError("audio_path_required")

        if not self.model_dir:
            raise RuntimeError("stt_model_dir_required")

        try:
            whisper_model_class = _load_whisper_model_class()
        except Exception as exc:
            raise RuntimeError("faster_whisper_dependency_unavailable") from exc

        model = whisper_model_class(self.model_dir)
        segments, _info = model.transcribe(normalized_audio_path)

        transcript = " ".join(
            str(getattr(segment, "text", "")).strip()
            for segment in segments
            if str(getattr(segment, "text", "")).strip()
        ).strip()

        if not transcript:
            raise RuntimeError("stt_transcription_empty")

        return transcript

from __future__ import annotations

from pathlib import Path
from typing import Any
import wave


# Non-functional alignment touch: hwalignspec closure marker.
def _load_piper_voice_class() -> Any:
    from piper.voice import PiperVoice  # type: ignore

    return PiperVoice


class PiperTTSProvider:
    def __init__(self, model_path: str, config_path: str) -> None:
        self.model_path = str(model_path).strip()
        self.config_path = str(config_path).strip()

    def synthesize_to_file(self, text: str, output_path: str) -> str:
        normalized_text = str(text).strip()
        normalized_output_path = str(output_path).strip()

        if not normalized_text:
            raise RuntimeError("tts_text_required")
        if not self.model_path:
            raise RuntimeError("tts_model_path_required")
        if not self.config_path:
            raise RuntimeError("tts_config_path_required")
        if not normalized_output_path:
            raise RuntimeError("tts_output_path_required")

        model_file = Path(self.model_path)
        config_file = Path(self.config_path)
        if not model_file.exists() or not model_file.is_file():
            raise RuntimeError("tts_model_file_missing")
        if not config_file.exists() or not config_file.is_file():
            raise RuntimeError("tts_config_file_missing")

        try:
            piper_voice_class = _load_piper_voice_class()
        except Exception as exc:
            raise RuntimeError("piper_dependency_unavailable") from exc

        output_file = Path(normalized_output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            voice = piper_voice_class.load(
                model_path=str(model_file),
                config_path=str(config_file),
            )
            with wave.open(str(output_file), "wb") as wav_file:
                voice.synthesize(normalized_text, wav_file)
        except Exception as exc:
            raise RuntimeError("tts_synthesis_failed") from exc

        return str(output_file)

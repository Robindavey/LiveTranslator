import asyncio
from typing import Optional

import numpy as np

from .faster_whisper_backend import FasterWhisperBackend
from .whisper_cpp_backend import WhisperCppBackend
from ..config.config import AppSettings


class SpeechToTextEngine:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        if self.settings.use_whisper_cpp:
            self.backend = WhisperCppBackend(
                model_path=self.settings.model_path,
                beam_size=self.settings.beam_size,
            )
        else:
            self.backend = FasterWhisperBackend(
                model_name=self.settings.model_name,
                model_path=self.settings.model_path,
                beam_size=self.settings.beam_size,
            )

    async def transcribe(self, audio: np.ndarray, language: Optional[str] = None):
        language = language or self.settings.whisper_language
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self.backend.transcribe,
            audio,
            language,
        )

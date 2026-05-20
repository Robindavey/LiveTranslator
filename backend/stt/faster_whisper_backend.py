import logging
from typing import List, Optional

import numpy as np
import torch
from faster_whisper import WhisperModel

logger = logging.getLogger("live_translator.stt")


class FasterWhisperBackend:
    def __init__(self, model_name: str = "small", model_path: str = "", beam_size: int = 5):
        self.model_name = model_name
        self.model_path = model_path or None
        self.beam_size = beam_size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        self.model = WhisperModel(
            model_name,
            device=self.device,
            compute_type=self.compute_type,
            download_root=self.model_path,
        )
        logger.info("Faster Whisper initialized on %s with compute_type=%s", self.device, self.compute_type)

    def transcribe(self, audio: np.ndarray, language: str = "auto") -> List[dict]:
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        segments, _ = self.model.transcribe(
            audio,
            language=language,
            beam_size=self.beam_size,
            word_timestamps=True,
        )
        result = []
        for segment in segments:
            segment_data = {
                "text": segment.text.strip(),
                "start": float(segment.start),
                "end": float(segment.end),
            }
            result.append(segment_data)
        return result

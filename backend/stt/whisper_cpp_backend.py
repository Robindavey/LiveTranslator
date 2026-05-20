import logging
from typing import List, Optional

import numpy as np

logger = logging.getLogger("live_translator.stt")


try:
    import whispercpp
except ImportError:  # pragma: no cover
    whispercpp = None


class WhisperCppBackend:
    def __init__(self, model_path: str = "", beam_size: int = 5):
        if whispercpp is None:
            raise RuntimeError("whispercpp is not installed. Install it to enable the whisper.cpp backend.")
        self.model_path = model_path
        self.beam_size = beam_size
        self.model = whispercpp.Whisper(model_path)
        logger.info("whisper.cpp backend initialized with model_path=%s", model_path)

    def transcribe(self, audio: np.ndarray, language: str = "auto") -> List[dict]:
        audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
        self.model.full_default_params()
        self.model.decode(audio_int16, self.model.params)
        result = [{
            "text": self.model.get_segment_text(i).strip(),
            "start": float(self.model.get_segment_t0(i)),
            "end": float(self.model.get_segment_t1(i)),
        } for i in range(self.model.n_segments())]
        return result

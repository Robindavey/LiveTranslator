import logging
from typing import List

import numpy as np
import scipy.signal as signal
import torch

logger = logging.getLogger("live_translator.vad")


class SileroVAD:
    def __init__(self, sample_rate: int = 16000, threshold: float = 0.5, window_seconds: float = 0.4):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.window_seconds = window_seconds
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        try:
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                verbose=False,
            )
            self.model = model.to(self.device)
            self.get_speech_timestamps = utils[0]
            logger.info("Silero VAD loaded on %s", self.device)
        except Exception as exc:
            logger.exception("Failed to load Silero VAD: %s", exc)
            raise

    def _resample(self, audio: np.ndarray) -> np.ndarray:
        if self.sample_rate == 16000:
            return audio
        gcd = np.gcd(self.sample_rate, 16000)
        up = 16000 // gcd
        down = self.sample_rate // gcd
        return signal.resample_poly(audio, up, down)

    def get_speech_segments(self, audio: np.ndarray) -> List[dict]:
        mono_audio = np.asarray(audio, dtype=np.float32)
        if mono_audio.ndim > 1:
            mono_audio = np.mean(mono_audio, axis=1)
        mono_audio = self._resample(mono_audio)
        waveform = torch.from_numpy(mono_audio).float().to(self.device)
        timestamps = self.get_speech_timestamps(
            waveform,
            self.model,
            sampling_rate=16000,
            threshold=self.threshold,
        )
        return timestamps

    def has_speech(self, audio: np.ndarray) -> bool:
        segments = self.get_speech_segments(audio)
        return len(segments) > 0

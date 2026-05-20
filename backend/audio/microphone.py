import asyncio
import logging
from typing import Callable

import numpy as np
import sounddevice as sd


logger = logging.getLogger("live_translator.audio")


class MicrophoneCapture:
    def __init__(self, sample_rate: int, frame_duration: float, callback: Callable[[np.ndarray], None]):
        self.sample_rate = sample_rate
        self.frame_duration = frame_duration
        self.callback = callback
        self.stream = None
        self.loop = asyncio.get_event_loop()

    def _audio_callback(self, indata, frames, time, status):
        if status:
            logger.debug("Microphone status: %s", status)
        if indata is None:
            return

        try:
            audio_frame = np.asarray(indata, dtype=np.float32)
            if audio_frame.ndim > 1:
                audio_frame = np.mean(audio_frame, axis=1)
            self.loop.call_soon_threadsafe(self.callback, audio_frame)
        except Exception as exc:
            logger.exception("Microphone callback failure: %s", exc)

    def start(self):
        try:
            block_size = int(self.sample_rate * self.frame_duration)
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=block_size,
                callback=self._audio_callback,
            )
            self.stream.start()
            logger.info("Microphone capture started at %s Hz", self.sample_rate)
        except Exception as exc:
            logger.warning("Unable to start microphone capture: %s", exc)
            self.stream = None

    def stop(self):
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
                logger.info("Microphone capture stopped")
            except Exception as exc:
                logger.warning("Failed to stop microphone capture: %s", exc)

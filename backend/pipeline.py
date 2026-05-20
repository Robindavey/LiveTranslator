import asyncio
import logging
from typing import Callable, List, Optional

import numpy as np

from .config.config import AppSettings
from .stt.engine import SpeechToTextEngine
from .translation.translation import build_translation_provider
from .vad.silero_vad import SileroVAD

logger = logging.getLogger("live_translator.pipeline")


class SpeechPipeline:
    def __init__(self, settings: AppSettings, broadcast_callback: Callable[[dict], None]):
        self.settings = settings
        self.broadcast_callback = broadcast_callback
        self.queue: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=64)
        self.stt_engine = SpeechToTextEngine(settings)
        self.vad = SileroVAD(
            sample_rate=settings.sample_rate,
            threshold=settings.vad_threshold,
            window_seconds=settings.vad_window_seconds,
        )
        self.translation_provider = build_translation_provider(settings)
        self.task: Optional[asyncio.Task] = None
        self.buffer: np.ndarray = np.zeros((0,), dtype=np.float32)
        self.source_language: str = settings.whisper_language or "auto"
        self.target_language: str = settings.whisper_language or "auto"
        self.direction: str = "user1-to-user2"

    def set_language_pair(self, source_language: str, target_language: str, direction: str = "user1-to-user2"):
        self.source_language = source_language
        self.target_language = target_language
        self.direction = direction
        self._broadcast_state(
            "ready",
            progress=0,
            state_label=f"Ready: {source_language} → {target_language}",
        )

    def _broadcast_state(self, state: str, progress: int | None = None, state_label: str | None = None):
        payload = {
            "type": "state.update",
            "state": state,
            "stateLabel": state_label or state,
        }
        if progress is not None:
            payload["progress"] = progress
        self.broadcast_callback(payload)

    async def start(self):
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self._run())
            logger.info("Speech pipeline started")

    async def stop(self):
        if self.task is not None:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                logger.info("Speech pipeline stopped")

    def enqueue_audio(self, samples: np.ndarray):
        try:
            self.queue.put_nowait(samples)
        except asyncio.QueueFull:
            logger.warning("Audio queue is full, dropping audio frame")

    async def _run(self):
        while True:
            chunk = await self.queue.get()
            self.buffer = np.concatenate((self.buffer, chunk))
            duration = len(self.buffer) / self.settings.sample_rate
            if duration >= self.settings.chunk_size_seconds:
                await self._process_buffer(self.buffer)
                self.buffer = np.zeros((0,), dtype=np.float32)

    async def _process_buffer(self, audio: np.ndarray):
        if not self.vad.has_speech(audio):
            logger.debug("No speech detected in audio buffer")
            return

        self._broadcast_state("listening", progress=10, state_label="Speech detected")
        self._broadcast_state("transcribing", progress=25, state_label="Transcribing audio")
        segments = await self.stt_engine.transcribe(audio, language=self.source_language)
        logger.debug("STT segments: %s", segments)

        self._broadcast_state("translating", progress=50, state_label="Translating text")
        for segment in segments:
            translated_text = self.translation_provider.translate(
                segment["text"],
                source_language=self.source_language,
                target_language=self.target_language,
            )
            self._broadcast_state("translating", progress=80, state_label="Finalizing translation")
            payload = {
                "type": "transcript.final",
                "text": segment["text"],
                "translated": translated_text,
                "start": segment["start"],
                "end": segment["end"],
                "direction": self.direction,
                "input_language": self.source_language,
                "output_language": self.target_language,
            }
            self.broadcast_callback(payload)
        self._broadcast_state("ready", progress=100, state_label="Ready for next turn")

    async def transcribe_snippet(self, audio: np.ndarray):
        if not self.vad.has_speech(audio):
            return []
        return await self.stt_engine.transcribe(audio)

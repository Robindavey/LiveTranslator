from pathlib import Path

from pydantic import BaseSettings


class AppSettings(BaseSettings):
    app_name: str = "LiveTranslator"
    host: str = "0.0.0.0"
    port: int = 8000

    # Speech-to-text defaults
    model_name: str = "small"
    model_path: str = ""
    whisper_language: str = "auto"
    beam_size: int = 5
    chunk_size_seconds: float = 4.0
    sample_rate: int = 16000

    # VAD
    vad_threshold: float = 0.5
    vad_window_seconds: float = 0.4
    vad_speech_padding_seconds: float = 0.4

    # Runtime behavior
    enable_mic_capture: bool = True
    translation_provider: str = "local"
    local_translation_model_path: str = ""
    enable_tts: bool = False
    tts_provider: str = "piper"
    use_whisper_cpp: bool = False
    max_websocket_clients: int = 12
    allow_remote_control: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

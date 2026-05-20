from abc import ABC, abstractmethod
from typing import Optional

from ..config.config import AppSettings


class TranslationProvider(ABC):
    def __init__(self, settings: AppSettings):
        self.settings = settings

    @abstractmethod
    def translate(self, text: str, source_language: str, target_language: str) -> str:
        pass


class LocalTranslationProvider(TranslationProvider):
    def translate(self, text: str, source_language: str, target_language: str) -> str:
        if source_language == target_language or target_language.lower() == "auto":
            return text
        return f"[translated {source_language}->{target_language}] {text}"


class ApiTranslationProvider(TranslationProvider):
    def translate(self, text: str, source_language: str, target_language: str) -> str:
        return f"[api translated {source_language}->{target_language}] {text}"


def build_translation_provider(settings: AppSettings) -> TranslationProvider:
    if settings.translation_provider.lower() == "api":
        return ApiTranslationProvider(settings)
    return LocalTranslationProvider(settings)

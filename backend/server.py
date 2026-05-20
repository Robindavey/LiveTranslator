import asyncio
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .audio.microphone import MicrophoneCapture
from .config.config import AppSettings
from .pipeline import SpeechPipeline
from .websocket.server import manager, router

root_logger = logging.getLogger("live_translator")


def create_app() -> FastAPI:
    settings = AppSettings()
    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.state.pipeline = SpeechPipeline(
        settings,
        broadcast_callback=lambda payload: asyncio.create_task(manager.broadcast(payload)),
    )
    app.include_router(router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def root():
        return FileResponse(frontend_dir / "index.html")

    @app.on_event("startup")
    async def startup_event():
        logging.basicConfig(level=settings.log_level)
        root_logger.info("Starting %s on %s:%s", settings.app_name, settings.host, settings.port)

        if not isinstance(app.state.pipeline, SpeechPipeline):
            raise RuntimeError("SpeechPipeline failed to initialize")

        await app.state.pipeline.start()

        if settings.enable_mic_capture:
            app.state.microphone = MicrophoneCapture(
                sample_rate=settings.sample_rate,
                frame_duration=settings.vad_window_seconds,
                callback=app.state.pipeline.enqueue_audio,
            )
            app.state.microphone.start()

    @app.on_event("shutdown")
    async def shutdown_event():
        if hasattr(app.state, "microphone"):
            app.state.microphone.stop()
        await app.state.pipeline.stop()

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "backend": "LiveTranslator"}

    @app.get("/config")
    async def config():
        return {"model_name": settings.model_name, "sample_rate": settings.sample_rate}

    return app


if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host=AppSettings().host, port=AppSettings().port, log_level=AppSettings().log_level.lower())

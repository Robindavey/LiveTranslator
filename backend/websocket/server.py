import base64
import json
import logging
from typing import List

import numpy as np
import scipy.signal as signal
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("live_translator.websocket")
router = APIRouter()


def decode_audio_payload(payload: dict, target_rate: int = 16000) -> np.ndarray | None:
    data = payload.get("data")
    sample_rate = int(payload.get("sample_rate", target_rate))
    fmt = payload.get("format", "int16")
    if not data or fmt != "int16":
        return None

    try:
        raw_bytes = base64.b64decode(data)
        audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if sample_rate != target_rate:
            gcd = np.gcd(sample_rate, target_rate)
            up = target_rate // gcd
            down = sample_rate // gcd
            audio = signal.resample_poly(audio, up, down)
        return audio
    except Exception as exc:
        logger.warning("Failed to decode audio payload: %s", exc)
        return None


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected (%d active)", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected (%d active)", len(self.active_connections))

    async def send_json(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        stale = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as exc:
                logger.warning("Broadcast failed: %s", exc)
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/ws/live")
async def live_transcribe(websocket: WebSocket):
    await manager.connect(websocket)
    pipeline = websocket.app.state.pipeline
    await manager.send_json(websocket, {
        "type": "state.update",
        "state": "ready",
        "stateLabel": "Ready to translate",
        "progress": 0,
        "input_language": pipeline.source_language,
        "output_language": pipeline.target_language,
        "direction": pipeline.direction,
    })
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_json(websocket, {"type": "error", "message": "Invalid JSON"})
                continue

            if payload.get("type") == "ping":
                await manager.send_json(websocket, {"type": "pong"})
                continue

            if payload.get("type") == "hello":
                await manager.send_json(websocket, {"type": "welcome", "message": "LiveTranslator connected"})
                continue

            if payload.get("type") == "language.update":
                pipeline = websocket.app.state.pipeline
                source_language = payload.get("sourceLanguage", "auto")
                target_language = payload.get("targetLanguage", "auto")
                direction = payload.get("direction", "user1-to-user2")
                pipeline.set_language_pair(source_language, target_language, direction)
                await manager.send_json(websocket, {
                    "type": "ack",
                    "message": "language.updated",
                    "sourceLanguage": source_language,
                    "targetLanguage": target_language,
                    "direction": direction,
                })
                continue

            if payload.get("type") == "audio.raw":
                audio = decode_audio_payload(payload)
                if audio is None:
                    await manager.send_json(websocket, {"type": "error", "message": "Unsupported audio payload"})
                    continue

                pipeline = websocket.app.state.pipeline
                pipeline.enqueue_audio(audio)
                await manager.send_json(websocket, {"type": "ack", "message": "audio.received"})
                continue

            await manager.send_json(websocket, {"type": "info", "message": "Message received"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

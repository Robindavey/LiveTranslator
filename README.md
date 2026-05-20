# LiveTranslator

A local, offline-first real-time multilingual speech translation backend.

## Features

- Real-time microphone capture
- Faster Whisper STT primary engine
- Optional whisper.cpp STT backend
- Silero VAD for speech detection
- WebSocket streaming support
- Modular translation provider architecture
- Docker-ready deployment
- Environment-based configuration

## Quick start

1. Copy `.env.example` to `.env` and tune settings.
2. Install dependencies:
   ```bash
   ./setup.sh build
   ```
3. Start the backend:
   ```bash
   ./setup.sh start
   ```
4. Open the web UI in your browser:
   ```
   http://<server-ip>:8000/
   ```
5. Stop the backend:
   ```bash
   ./setup.sh stop
   ```

## Browser Web UI

- The backend now serves a web interface at `/`.
- You can connect from any device on the same network.
- The page captures microphone audio and streams it to the backend for live transcription.

## WebSocket API

- `ws://localhost:8000/ws/live`
- Send JSON messages like:
  - `{ "type": "ping" }`
  - `{ "type": "hello" }`
- The server broadcasts transcript events with `type: transcript.final`.

## Notes

- The default STT model is `small` for balanced latency and accuracy.
- For CPU-only or edge environments, set `USE_WHISPER_CPP=true` and provide a local whisper.cpp model.
- The default microphone path uses the system default input device and is enabled with `ENABLE_MIC_CAPTURE=true`.

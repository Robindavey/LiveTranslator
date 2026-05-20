# LiveTranslator Implementation Summary

This document summarizes the features and components implemented so far for the LiveTranslator project.

## Architecture

- Python backend with modular structure under `backend/`
- Frontend served by FastAPI static routes from `frontend/`
- WebSocket-based live streaming API for browser clients
- Local-first design with offline-capable STT and translation flow
- Docker support via `Dockerfile`
- Environment-driven configuration with `.env.example`
- Shell automation and deployment helper via `setup.sh`

## Key Components

### Backend modules

- `backend/config/config.py`
  - Application settings via `pydantic.BaseSettings`
  - Configurable model name, beam size, chunk size, VAD parameters, translation provider, TTS provider, and more

- `backend/audio/microphone.py`
  - Real-time microphone capture using `sounddevice`
  - Async callback integration for low-latency audio streaming

- `backend/vad/silero_vad.py`
  - Speech detection using Silero VAD
  - Audio resampling and detection of speech segments

- `backend/stt/faster_whisper_backend.py`
  - Primary STT engine using `faster-whisper`
  - GPU acceleration when available, CPU-compatible fallback

- `backend/stt/whisper_cpp_backend.py`
  - Optional `whisper.cpp` STT backend for CPU-only / low-memory environments

- `backend/stt/engine.py`
  - Runtime backend selection between Faster Whisper and whisper.cpp
  - Async transcription wrapper

- `backend/translation/translation.py`
  - Modular translation provider architecture
  - Local and API provider stubs for future extension

- `backend/pipeline.py`
  - Streaming speech pipeline: VAD → chunking → STT → translation
  - Language pair state, direction handling, and progress broadcast events
  - Final transcript payloads include source/target languages and direction metadata

- `backend/websocket/server.py`
  - WebSocket connection management for multiple clients
  - Accepts browser audio frames via JSON audio payloads
  - Handles language updates, direction changes, acknowledgements, and state progress events

- `backend/server.py`
  - FastAPI application setup with CORS and static frontend hosting
  - Health and config endpoints
  - Startup/shutdown lifecycle for pipeline and microphone capture

### Frontend

- `frontend/index.html`
  - Browser UI for remote access from any device
  - Input/output language selection
  - Direction toggle for alternating speaker turns
  - Translation progress bar and status display

- `frontend/app.js`
  - WebSocket client to connect to `/ws/live`
  - Microphone capture and audio streaming using Web Audio API
  - Language update messages and direction control
  - Real-time transcript and state updates in the UI

- `frontend/style.css`
  - Responsive UI styling for controls, language selectors, progress bar, and transcript panels

### Project tooling

- `requirements.txt`
  - Backend Python dependencies including FastAPI, Uvicorn, faster-whisper, torch, sounddevice, and more

- `Dockerfile`
  - Slim Python image with dependencies installed
  - Serves backend on port `8000`

- `setup.sh`
  - Build/install dependencies
  - Start/stop/restart/status backend process
  - Update repository and rebuild
  - New `checkout` command for Linux server branch switching and rebuild

## User-facing capabilities

- Real-time microphone transcription from browser clients
- Multi-language language selection for input and output
- Bidirectional conversation flow:
  - `User 1 speaks in L1 → translates to L2`
  - `User 2 speaks in L2 → translates to L1`
- Clear state feedback and translation progress indicators
- Web-based remote access from any device on the same network
- Optional CPU-first STT path with whisper.cpp
- Local translation provider architecture ready for LLM or API providers

## Notes

- The current translation provider is a stub and returns placeholder translation text for local translation.
- The system is designed for extensibility and production readiness, with clear separation of concerns in backend modules.
- Future work can include real TTS, diarization, punctuation restoration, subtitle export, and mobile-optimized UI.

"""
Główny serwer HTTP (FastAPI) dla daemona Audio Service.

Wystawia 2 wyizolowane endpointy REST dla zmysłów mowy:
- POST /v1/stt/transcribe (Transkrypcja mowy STT)
- POST /v1/tts/synthesize (Synteza mowy TTS)
- GET /health (Stan operacyjny usługi)
"""
import argparse
import sys
import asyncio
import logging
import httpx
import uvicorn
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from audio_service.stt import STTEngine
from audio_service.tts import TTSEngine

logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    hb_task = asyncio.create_task(_heartbeat_loop())
    yield
    hb_task.cancel()

app = FastAPI(title="Regis Audio Service (STT + TTS)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stt_engine = STTEngine(model_size="small", language="pl")
tts_engine = TTSEngine(voice_name="pl_PL-darkman-medium")

_controller_url: str = "http://127.0.0.1:8000"
_service_port: int = 8002


async def _heartbeat_loop():
    """Pętla wysyłająca rejestrację i heartbeat do Kontrolera."""
    registered_once = False
    while True:
        try:
            payload = {
                "id": "audio-service-standalone",
                "name": "Lokalny Audio Service (Faster-Whisper + Piper)",
                "host": "127.0.0.1",
                "port": _service_port,
                "stt_model_size": stt_engine.model_size,
                "tts_model_name": tts_engine.voice_name,
            }
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(f"{_controller_url}/v1/audio/register", json=payload)
                if resp.status_code == 200:
                    if not registered_once:
                        logger.info(f"[AudioService] Połączono i zarejestrowano zmysł mowy w Kontrolerze ({_controller_url}).")
                        registered_once = True
        except Exception:
            registered_once = False
        await asyncio.sleep(15)


@app.get("/health")
@app.get("/v1/status")
async def health_check():
    """Zwraca status operacyjny usługi Audio Service."""
    return {
        "status": "ready",
        "stt_model": stt_engine.model_size,
        "tts_voice": tts_engine.voice_name,
        "service": "audio_service",
    }


@app.post("/v1/stt/transcribe")
async def transcribe_endpoint(request: Request, file: UploadFile = File(None)):
    """
    Endpoint transkrypcji mowy (STT).
    Przyjmuje plik audio jako multipart/form-data ('file') lub bezpośredni bufor bajtów.
    """
    if file:
        audio_bytes = await file.read()
    else:
        audio_bytes = await request.body()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Brak bajtów pliku audio do transkrypcji.")

    res = stt_engine.transcribe(audio_bytes)
    return JSONResponse(content=res)


@app.post("/v1/tts/synthesize")
async def synthesize_endpoint(request: Request):
    """
    Endpoint syntezy mowy (TTS).
    Przyjmuje JSON {"text": "tekst do przeczytania"}.
    Zwraca JSON {"audio_b64": "...", "elapsed_ms": 150}.
    """
    data = await request.json()
    text = data.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Brak parametru 'text' w żądaniu.")

    res = tts_engine.synthesize(text)
    return JSONResponse(content=res)


def main():
    global _service_port, _controller_url
    parser = argparse.ArgumentParser(description="Regis Audio Service Daemon")
    parser.add_argument("--host", default="127.0.0.1", help="Host sieciowy")
    parser.add_argument("--port", type=int, default=8002, help="Port serwera HTTP")
    parser.add_argument("--controller-url", default="http://127.0.0.1:8000", help="URL Kontrolera Regis")
    args = parser.parse_args()

    _service_port = args.port
    _controller_url = args.controller_url

    print(f"[AudioService] Uruchamianie daemona Audio Service na http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()

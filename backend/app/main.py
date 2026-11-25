import json
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, SessionLocal, engine, get_db
from .transcriber import SAMPLE_RATE, transcribe

log = logging.getLogger("stt")
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Speech to Text")

CHUNK_SECONDS = 4  # transcribe every ~4s of audio for near real-time output
CHUNK_BYTES = SAMPLE_RATE * 2 * CHUNK_SECONDS


# ---------- CRUD ----------
@app.get("/api/transcriptions", response_model=list[schemas.TranscriptionOut])
def list_items(db: Session = Depends(get_db)):
    return db.scalars(
        select(models.Transcription).order_by(models.Transcription.id.desc())
    ).all()


@app.post("/api/transcriptions", response_model=schemas.TranscriptionOut, status_code=201)
def create_item(data: schemas.TranscriptionIn, db: Session = Depends(get_db)):
    item = models.Transcription(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/api/transcriptions/{item_id}", response_model=schemas.TranscriptionOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Transcription, item_id)
    if not item:
        raise HTTPException(404, "Not found")
    return item


@app.put("/api/transcriptions/{item_id}", response_model=schemas.TranscriptionOut)
def update_item(item_id: int, data: schemas.TranscriptionUpdate, db: Session = Depends(get_db)):
    item = db.get(models.Transcription, item_id)
    if not item:
        raise HTTPException(404, "Not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/api/transcriptions/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Transcription, item_id)
    if not item:
        raise HTTPException(404, "Not found")
    db.delete(item)
    db.commit()


# ---------- Real-time transcription ----------
@app.websocket("/ws/transcribe")
async def ws_transcribe(ws: WebSocket):
    """Client sends 16kHz mono int16 PCM as binary frames, then text 'stop'."""
    await ws.accept()
    buf = bytearray()
    total_bytes = 0
    pieces: list[str] = []

    async def flush(data: bytes):
        try:
            text = await transcribe(bytes(data))
        except Exception as e:  # report but keep session alive
            log.exception("transcribe failed")
            await ws.send_json({"type": "error", "message": str(e)})
            return
        if text:
            pieces.append(text)
            await ws.send_json({"type": "partial", "text": text})

    try:
        while True:
            msg = await ws.receive()
            if msg.get("bytes"):
                buf.extend(msg["bytes"])
                total_bytes += len(msg["bytes"])
                while len(buf) >= CHUNK_BYTES:
                    chunk, buf = bytes(buf[:CHUNK_BYTES]), buf[CHUNK_BYTES:]
                    await flush(chunk)
            elif msg.get("text") is not None:
                if json.loads(msg["text"]).get("action") == "stop":
                    break
            elif msg.get("type") == "websocket.disconnect":
                return
    except WebSocketDisconnect:
        return

    if len(buf) > SAMPLE_RATE:  # remainder > 0.5s
        await flush(bytes(buf))

    full = " ".join(pieces).strip()
    saved_id = None
    if full:
        db = SessionLocal()
        try:
            item = models.Transcription(
                title=full[:40], text=full, duration_sec=round(total_bytes / (SAMPLE_RATE * 2), 1)
            )
            db.add(item)
            db.commit()
            saved_id = item.id
        finally:
            db.close()
    await ws.send_json({"type": "final", "id": saved_id, "text": full})
    await ws.close()


# ---------- Frontend ----------
FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")

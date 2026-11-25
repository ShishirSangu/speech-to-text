# Real-time Speech to Text (Hindi + English)

Speak into the mic and get a live transcription (mixed Hindi/English supported).
Transcriptions are stored in PostgreSQL and managed from a dashboard with full CRUD.

**🔗 Live demo:** https://speech-to-text-kqzj.onrender.com/
*(Render free tier sleeps when idle, so the first load can take ~50 seconds.)*

**Stack:** FastAPI · SQLAlchemy · PostgreSQL (Neon) / SQLite locally · WebSocket streaming · Gemini speech-to-text · vanilla JS frontend (AudioWorklet) · deployed on Render.

## Features
- Real-time mic transcription over WebSocket (text appears about every 4 s while speaking)
- Multilingual: mixed Hindi (Devanagari) + English
- History dashboard with Create / Read / Update / Delete
- Automatic model fallback (`gemini-3.5-transcribe` → `gemini-3.5-flash` → …) when a model is overloaded (503) or rate-limited (429)
- Silence detection so empty audio is not sent to the API

## Architecture
```
Browser mic ─► AudioWorklet (16 kHz PCM) ─► WebSocket /ws/transcribe ─► FastAPI
                                                                          │ every ~4 s
                                                                          ▼
                                                              Gemini speech-to-text
                                                                          │
              live partial text ◄──────────────────────────────── FastAPI ┤
                                                                          ▼
                                                      PostgreSQL (saved on Stop)
```
FastAPI also serves the frontend, so the whole app is a single deployment.

## Run locally
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add GEMINI_API_KEY (free: https://aistudio.google.com/apikey)
uvicorn app.main:app --reload
```
Open http://localhost:8000 (the mic works on localhost and on HTTPS).

### Environment variables
| Name | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio key (required) |
| `GEMINI_MODEL` | Preferred model, default `gemini-3.5-transcribe` |
| `DATABASE_URL` | Postgres URL; empty = local SQLite |

## API
| Method | Path | Description |
|---|---|---|
| GET | `/api/transcriptions` | List all |
| POST | `/api/transcriptions` | Create |
| GET | `/api/transcriptions/{id}` | Read one |
| PUT | `/api/transcriptions/{id}` | Update title/text |
| DELETE | `/api/transcriptions/{id}` | Delete |
| WS | `/ws/transcribe` | Send 16 kHz mono int16 PCM frames, then `{"action":"stop"}` |

## Deploy (free)
Render web service (root `backend`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`) + Neon Postgres. Set `DATABASE_URL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `PYTHON_VERSION=3.11.9`.

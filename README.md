# Real-time Speech to Text (Hindi + English)

Speak into the mic and get a live transcription (mixed Hindi/English supported).
Transcriptions are stored in a relational DB and managed from a dashboard (CRUD).

**Stack:** FastAPI · SQLAlchemy (PostgreSQL / SQLite) · WebSocket streaming · Gemini speech-to-text · vanilla JS frontend (AudioWorklet).

## How it works
Browser captures mic → downsamples to 16 kHz PCM → streams over WebSocket → backend transcribes every ~4 s → partial text streams back live → on Stop the full text is saved to the DB.

## Run locally
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add GEMINI_API_KEY (free: https://aistudio.google.com/apikey)
uvicorn app.main:app --reload
```
Open http://localhost:8000 (mic works on localhost / HTTPS).

## API
`GET/POST /api/transcriptions` · `GET/PUT/DELETE /api/transcriptions/{id}` · `WS /ws/transcribe`

## Deploy (free)
Render web service (root `backend`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`) + Neon Postgres (`DATABASE_URL`) + `GEMINI_API_KEY`.

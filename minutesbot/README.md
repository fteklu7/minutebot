# MinutesBot

Turns meeting recordings into minutes: summary, decisions, and action items
with owners and due dates. Then you can search across every past meeting.

I'm the secretary for two student orgs, so after every meeting I'm turning a
recording or a page of scribbled notes into minutes and figuring out who said
they'd do what. I built this to do that part for me.

Upload a meeting recording (or a transcript) and it:

- transcribes it
- writes a short summary and pulls out decisions
- pulls out action items with who owns them and when they're due
  ("Jordan will book the room by Friday" -> Jordan, due Fri 11/13)
- tracks open action items across all meetings, with overdue ones flagged
- makes every past meeting searchable ("what did we decide about the food budget?")

<!-- TODO: add screenshot -->

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL
- **AI:** OpenAI Whisper (speech to text), GPT-4o mini (extraction), text embeddings (search)
- **Frontend:** React + Vite
- **Infra:** Docker Compose, nginx, GitHub Actions (tests on SQLite and Postgres)

## How it works

```
upload (audio or .txt)
   |
   v
FastAPI saves the meeting, returns 202 right away
   |
   v  background task
transcribe -> extract summary/decisions/action items (JSON)
   -> split transcript into chunks -> embed chunks -> status = done
   |
   v
React page polls until it's done
```

A few parts worth calling out:

**Search** (`backend/app/search.py`). Transcripts are split into ~120 word
chunks with one sentence of overlap, embedded, and searched with cosine
similarity. It's brute force in numpy, which is fine for an org's worth of
meetings (a semester is a few hundred chunks). If this ever had to handle much
more, I'd move it into Postgres with pgvector.

**Relative due dates.** People say "by Friday", not "by 2026-11-13". The model
gets the meeting's date and weekday so it can turn "Friday" into a real date,
and it's told not to make up dates that weren't said.

**Not trusting the model's output** (`backend/app/ai.py`). The model is asked for
JSON, but the response is still validated: code fences stripped, items with no
task dropped, bad dates thrown out instead of crashing.

**Offline mode.** Without an OpenAI key the app swaps in a rule-based provider
(regex for "X will ... by Friday", hashed word vectors for search). It's
nowhere near as good, but it means the tests and local dev don't need an API
key or cost money.

## Running it

### With Docker

```bash
cp .env.example .env     # add your OPENAI_API_KEY and an ACCESS_KEY
docker compose up --build
```

Open http://localhost:8080, enter the access key in the top right, then upload
a meeting.

### Without Docker

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload      # uses SQLite by default

# frontend (another terminal)
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

Put settings in `backend/.env` (same names as `.env.example`). With no API key
you can still upload `.txt` transcripts.

## Tests

```bash
cd backend
pytest
```

Runs on SQLite by default. To run against Postgres set
`TEST_DATABASE_URL=postgresql+psycopg2://user:pass@localhost/dbname`.
CI runs both.

## Limitations / what's next

- Single access key, no user accounts. It's a personal tool for now
- Uploads are capped at 25 MB (Whisper's limit). Longer recordings would need
  to be split into pieces before transcribing
- Processing runs in FastAPI background tasks, so if the server restarts
  mid-upload that meeting stays stuck on "processing". A real job queue
  (Redis + RQ or Celery) would fix that
- No database migrations yet (tables are created on startup). Alembic is next
  if the schema changes
- Speaker labels ("who said what") would make owner detection better

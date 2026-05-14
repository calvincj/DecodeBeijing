# DecodeBeijing

I built this because I kept reading analyses of Chinese policy that felt either too vague ("Beijing is shifting its tone on X") or too anecdotal (one quote from one speech). I wanted something more systematic — a way to actually track how the Chinese government talks about specific terms across decades of official documents.

DecodeBeijing is a political language tracker that indexes key terms across major Chinese government documents: Five-Year Plans, Government Work Reports, Economic Work Conferences, Third Plenary Sessions, Party Congresses, and more. For any term, you can see how frequently it appears over time, where it ranks in the government's numbered policy task lists, and how the framing around it has shifted — all in one place.

## What it does

- **Frequency over time** — tracks mentions of a term across all indexed documents, with a smoothing option that spreads Five-Year Plan and plenum counts across their full term so you're not just seeing one-year spikes
- **Policy task priority** — shows where a term appears in the government's numbered task lists (Task 1 = top priority), so you can see if something is being pushed up or down the agenda
- **Government framing** — AI-generated summaries of how each document contextualizes a term, so you can track rhetorical shifts without reading every document yourself
- **Custom search** — look up any Chinese term, not just the pre-tracked ones
- **Document browser** — read the source documents and see which terms appear in each one

## Stack

- **Backend**: FastAPI + SQLAlchemy (async) + PostgreSQL
- **Frontend**: Next.js + TypeScript + Recharts
- **NLP**: jieba for Chinese tokenization, DeepL for translations
- **AI framing**: OpenRouter API (non-Chinese models only, given content sensitivity)

## Running locally

**Backend**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your DATABASE_URL and API keys
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Then open `http://localhost:3000`.

## Data pipeline

Documents are ingested via scripts in `scripts/` and `backend/pipeline/`. After ingestion, run `analyze_document.py` to compute term frequencies and generate AI framing summaries. The pipeline is one-time setup — the web app just reads from the database.

---

Built as a personal project to better understand how Chinese policy language evolves over time.

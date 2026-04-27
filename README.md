# AI Resume Engine (MVP)

FastAPI service for uploading resumes, storing files locally, and persisting parsed text, keyword skills, and experience (years) in SQLite or MySQL.

**Phase 1:** Resume status flow (`uploaded` → `parsing` → `parsed` / `failed`), one row per resume in `resume_parsed_data`, structured API responses, 5 MB max uploads, `.pdf` / `.docx` / `.txt` only.

## Setup

```bash
cd ai-resume-engine
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Set `DATABASE_URL` for MySQL when needed (`mysql+pymysql://...`). After model changes, recreate tables or run your own migrations (`sqlalchemy` `create_all` does not alter existing tables).

## Run

```bash
uvicorn app.main:app --reload
```

- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Frontend UI: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Health: `GET /health`

On first startup a demo user is created (`id=1`, `demo@example.com`). Uploads default to `user_id=1` if you omit the form field.

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Multipart file + optional `user_id` (form) |
| GET | `/api/resumes` | List resumes; optional `user_id` query |
| GET | `/api/resumes/{id}` | `id`, `status`, `file_name`, `parsed_data` (`skills`, `experience_years`) |
| DELETE | `/api/resumes/{id}` | Delete DB row and stored file |

Allowed extensions: `.pdf`, `.docx`, `.txt`. Max size: 5 MB (see `app/core/config.py` and `.env`).

## Layout

See the repository tree: `app/main.py` (entry), `core/` (settings + DB), `models/`, `schemas/`, `api/routes/`, `services/`, `utils/`, and `uploads/` for local disk storage.

## Frontend

A minimal frontend is available at `/` and is served by FastAPI from the `frontend/` folder.

Features:
- Upload resume (`POST /api/upload`)
- List resumes (`GET /api/resumes`)
- View parsed detail (`GET /api/resumes/{id}`)
- Delete resume (`DELETE /api/resumes/{id}`)

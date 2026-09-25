# Litera

Litera is an e-book reading and learning platform evolved from the original Web-Perpustakaan project. Available digital editions can be read directly in the browser; physical circulation is an additional library service rather than the primary experience.

## Overview

This repository is being refactored from the legacy PHP application into a new foundation for a digital library and learning platform.

## Planned Tech Stack

- Frontend: Vue 3, TypeScript, Vite
- Backend: Python, FastAPI
- Database: PostgreSQL

## Repository Structure

```text
legacy/perpus-app/  Original PHP Web-Perpustakaan project
frontend/          Vue 3 frontend foundation
backend/           FastAPI backend foundation
storage/           Local development storage for uploaded digital books
docs/              Architecture, database, API, and AI documentation
scripts/           Project scripts
```

## Legacy Project

The original PHP project is preserved under `legacy/perpus-app/` as a historical version. Its source code has not been rewritten during this foundation phase.

## Development Status

Litera currently includes the project foundation, catalog database schema, authentication, membership lifecycle, catalog API, user and admin workspaces, physical circulation, a native extracted-text reader, Learning Mode, cached AI summaries, and admin-reviewed AI quiz drafts. Fines, notifications, EPUB reading, OCR, RAG, AI chat, and ML recommendations are not implemented yet.

## Backend Setup

From `backend/`, create and activate a virtual environment, then run:

```bash
pip install -r requirements.txt
```

Create `.env` from `.env.example`, set `DATABASE_URL` and a private `JWT_SECRET_KEY`, then apply the schema and start the API:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

## Frontend Setup

From `frontend/`, install dependencies and start Vite:

```bash
npm install
npm run dev
```

Set `VITE_API_BASE_URL` when the API is not available at `http://localhost:8000`.

## Digital Reader

Admin PDF uploads are stored beneath `storage/books/<edition-id>/` using generated names; database rows store only storage keys. The API validates PDF extension, MIME type, signature, and `MAX_BOOK_FILE_SIZE_MB`, then synchronously extracts page-aware text with `pypdf`. PDF outlines become chapters when available, otherwise Litera creates one `Full Document` chapter.

PDF bytes are served only through the access-controlled API with HTTP range support. Reading is inline by default; downloads require the file's `allow_download` setting. Replacement and deletion are blocked while an edition has reading progress or bookmarks, preventing silent invalidation of page references. Processing stays synchronous for local V1 use; a job queue should only be introduced when real upload latency requires it.

## Learning Mode

Learning Mode is available to active members for educational, non-fiction, and reference books. Admins author multiple-choice chapter quizzes as drafts, preview them, and publish them when ready. Answers remain editable until explicit submission; grading happens only on the backend and answer keys are returned only with completed results.

Quiz structure and deletion are locked after the first attempt exists so historical attempts remain valid. Retakes create separate attempts, while edition progress is derived from reading progress and each quiz's best completed score rather than stored as a redundant percentage.

## AI Summaries

Summary generation is an optional admin-controlled feature. Configure AI_PROVIDER, AI_API_KEY, AI_MODEL, and optionally AI_BASE_URL, AI_TEMPERATURE, and AI_MAX_OUTPUT_TOKENS in the backend environment. The current provider uses an OpenAI-compatible chat-completions HTTP endpoint; the rest of Litera starts and works normally without these values.

Summaries are generated only from extracted Litera page content. Long chapters are processed in bounded chunks, while book summaries combine fresh chapter summaries hierarchically. A SHA-256 source hash prevents repeated generation and marks summaries stale when extracted content changes. Fiction uses the spoiler-free prompt policy. Only admins generate or regenerate summaries, and only active members can read persisted, current READY results.

## AI Quiz Drafts

Admins can generate a 3-20 question quiz draft from an eligible chapter at `POST /api/v1/admin/chapters/{chapter_id}/quiz/generate` and regenerate an unpublished AI draft at `POST /api/v1/admin/quizzes/{quiz_id}/regenerate`. The backend resolves extracted chapter content itself; clients cannot submit arbitrary source text.

The provider returns JSON mode output that is validated with strict Pydantic schemas and the existing quiz-domain validation before one atomic persistence transaction. Generated quizzes use the normal `quizzes`, `quiz_questions`, and `quiz_options` tables with `generated_by=AI` and `is_published=false`. Admins review and edit them in the existing Quiz Editor, and publishing and student attempts continue through the Phase 8 Quiz Engine without any LLM call.

Quiz source is capped at 16,000 normalized characters. Oversized chapters are sampled across five evenly distributed sections instead of taking only the beginning. Generation is admin-only, request size is bounded, repeated clicks surface the existing draft, and a per-process chapter lock prevents concurrent duplicate requests. Regeneration updates an untouched draft in place; if attempt history exists, it creates a new draft and preserves the original quiz and attempts.

## Local Demo Accounts

Create or refresh local demo accounts and catalog data from `backend/`:

```bash
python -m scripts.seed_demo
```

The seed downloads 16 complete public-domain texts from Project Gutenberg, converts them into locally stored PDFs, and processes them for the Litera reader. Each title has one clearly tracked physical copy; public digital editions have unlimited concurrent access. Internet access is required only the first time each digital title is seeded.

All demo accounts use the password `LiteraDemo123!`:

- `admin.demo@example.com` - administrator workspace and circulation
- `member.demo@example.com` - active member with a loan and reservation
- `user.demo@example.com` - registered user without membership

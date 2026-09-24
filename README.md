# Litera

Litera is a digital library and learning platform evolved from the original Web-Perpustakaan project.

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
storage/           Future local storage for books, covers, and temporary files
docs/              Architecture, database, API, and AI documentation
scripts/           Project scripts
```

## Legacy Project

The original PHP project is preserved under `legacy/perpus-app/` as a historical version. Its source code has not been rewritten during this foundation phase.

## Development Status

Litera currently includes the project foundation, catalog database schema, backend authentication, membership lifecycle, the core catalog API, the Phase 5B user experience, and the Phase 5C admin workspace for catalog and membership management. File storage, borrowing, e-book reading, quizzes, AI summarization, RAG, and ML recommendations are not implemented yet.

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

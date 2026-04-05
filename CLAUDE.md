# CLAUDE.md (SHORT VERSION)

## Stack
Python 3.12+, FastAPI, PostgreSQL, SQLAlchemy (async), Alembic, Redis, Pydantic, Docker, Docker Compose, uv

---

## Core Rules

- Always use **async** where possible
- Always use **type hints**
- No business logic in routers
- No DB access outside repositories
- No secrets in code (env only)
- Keep code simple and predictable

---

## Architecture

Layers:
- api → HTTP only
- schemas → Pydantic
- models → SQLAlchemy
- repositories → DB access
- services → business logic
- core → config / utils
- db → session / engine

Flow:
API → Service → Repository → DB

---

## FastAPI

- Prefix: `/api/v1`
- Use `response_model`
- Explicit schemas for input/output
- Health endpoints required

---

## Database

- PostgreSQL only
- All changes via Alembic
- No manual schema edits
- Use `decimal` for money (never float)

---

## Redis

Use for:
- cache
- temporary data
- tokens[CLAUDE (1).md](CLAUDE%20%281%29.md)

Always:
- use TTL
- use namespaced keys

---

## Async

- No blocking calls in async routes
- Use async DB + Redis
- Heavy tasks → background worker

---

## Config

- ENV-based only
- Use settings module (Pydantic)
- Separate dev / prod

---

## Docker

- Each service → own Dockerfile
- Use docker-compose for dev
- Services:
  - backend
  - frontend
  - postgres
  - redis

---

## uv

- Use `uv sync`
- Use `uv run`
- No pip/venv unless necessary

---

## Code Style

- Small functions
- Clear naming
- No huge files
- Explicit > implicit

---

## Testing

- Test services + repositories
- Avoid external dependencies (mock)

---

## Feature Workflow

1. Define domain
2. Define API
3. Add schemas
4. Implement service
5. Implement repository
6. Add migration
7. Add tests

---

## Done Criteria

- Runs locally
- Runs in Docker
- Types valid
- Migrations applied
- No hardcoded config

---

## Anti-Patterns

- business logic in API
- direct DB in routes
- sync in async code
- float for money
- no migrations
- random dependencies

---

## Goal

Clean, async, typed, microservice-ready backend usable by humans and AI agents.

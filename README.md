# DocFlow AI

DocFlow AI is an AI data-entry automation platform. This repository currently contains the Sprint 1 foundation: a Next.js frontend, a FastAPI backend, PostgreSQL, and Docker Compose.

No OCR, LLM, document processing, upload workflow, or extraction features are implemented in this foundation.

## Run locally

1. Copy the example configuration:

   ~~~sh
   cp .env.example .env
   ~~~

2. Start the stack:

   ~~~sh
   docker compose up --build
   ~~~

3. Open the services:

   - Frontend: http://localhost:3000
   - API health check: http://localhost:8000/health
   - API documentation: http://localhost:8000/docs

The health endpoint verifies that FastAPI can connect to PostgreSQL. Stop the stack with:

~~~sh
docker compose down
~~~

Use `docker compose down -v` only when you intentionally want to remove the local PostgreSQL and document-storage volumes.

## Repository layout

~~~text
.
├── frontend/       Next.js, TypeScript, Tailwind CSS
├── backend/        FastAPI and PostgreSQL connection code
├── compose.yaml    Local multi-container stack
└── .env.example    Safe local configuration template
~~~

## Foundation decisions

- PostgreSQL is the initial application database.
- The backend uses a small Psycopg connection helper; schemas and migrations will be introduced with the first persisted feature.
- Docker creates a private named volume for future document storage. No file-upload endpoint exists yet.
- The development credentials in .env.example are not suitable for deployment.

# DocFlow AI

DocFlow AI is an AI data-entry automation platform. This repository currently contains the Sprint 1 foundation: a Next.js frontend, a FastAPI backend, PostgreSQL, and Docker Compose.

The upload foundation and normalized OCR service are implemented. LLM extraction
and background job orchestration remain out of scope.

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
- `POST /documents` accepts a multipart `file`, `owner_user_id`, `document_type_id`, and `schema_id`. The legacy-compatible alias is `POST /documents/upload`.
- Uploads accept PDF, PNG, and JPEG only, verify the file signature rather than trusting the declared MIME type, enforce a 10 MiB default limit, and record a SHA-256 checksum.
- Original files use opaque keys in the private Docker volume; they are never exposed as public URLs. The database metadata is written only after storage succeeds, and the stored object is removed if metadata persistence fails.
- Uploading does not queue or run OCR, LLM, or other processing. OCR is exposed
  as a worker-oriented service and stores a private, versioned page/block
  artifact for a later extraction stage.
- The development credentials in .env.example are not suitable for deployment.

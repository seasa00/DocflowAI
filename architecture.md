# AI Data Entry Automation Platform

## Architecture and TODO Plan

This document defines a realistic Version 1 architecture for an AI data-entry automation platform. It contains product direction, system design, and delivery planning only; it does not prescribe implementation code.

The product is broader than invoice extraction. Its purpose is to convert unstructured documents into reviewed, structured database records. Invoices are the first V1 workflow because their fields, validation rules, and success criteria are easy to demonstrate. The data model and pipeline must allow receipts, resumes, forms, and business documents to be added later without rebuilding the platform.

## 1. Product vision

### Business problem

Many organizations receive information in PDFs, photos, scanned forms, and other documents, then manually copy that information into spreadsheets or databases. This work is slow, error-prone, difficult to audit, and expensive to scale. The same facts may also be entered in different formats by different people, which makes downstream reporting and automation unreliable.

The platform reduces this manual data-entry work. A user uploads a document, the system reads it, proposes data that matches a known schema, validates the proposal, and sends uncertain or incomplete values to a human reviewer. The approved result becomes a structured record that can be searched, exported, or retrieved through an API.

### Why AI is useful

Traditional OCR can read characters but does not reliably determine what a value means. For example, an invoice may contain several dates, many monetary amounts, and several addresses. AI document understanding adds semantic interpretation: it can distinguish an invoice number from a purchase-order number and a total from a subtotal.

AI is an assistant in this architecture, not the source of truth. The system combines:

- OCR and native PDF text extraction to obtain document content.
- An LLM to identify candidate values and their source evidence.
- Schema mapping to place those values into consistent field names and data types.
- Deterministic validation to catch malformed or implausible values.
- Human review before a V1 record is approved.

This combination improves speed without relying on the model to make unreviewed business decisions.

### V1 goal

V1 enables an authenticated user to upload one invoice PDF, JPEG, or PNG; receive a proposed invoice record; correct it in a review screen; approve it; and export or retrieve the approved structured data.

The first invoice schema should cover header-level fields only:

| Field | V1 behavior |
|---|---|
| Supplier name | Required before approval; may be initially empty |
| Invoice number | Required before approval and retained as text |
| Issue date | Required before approval when available; normalized only when unambiguous |
| Due date | Optional |
| Currency | Required before approval |
| Subtotal | Optional decimal |
| Tax amount | Optional decimal |
| Total amount | Required before approval |

Invoice line items are intentionally outside V1. The platform still stores the document type and schema version with each result so future document types can follow the same pipeline.

## 2. Product scope

### V1 features

| Area | V1 capability |
|---|---|
| Access | Authenticated, private user accounts with user-owned documents |
| Upload | PDF, JPEG, and PNG upload with server-side file, size, and page checks |
| Storage | Private storage for originals, page previews, and processing artifacts |
| Document type | A preconfigured Invoice document type selected at upload |
| Schema | One versioned invoice-header schema stored in the schema registry |
| Processing | Background extraction jobs with visible queued, processing, review, approved, and failed states |
| OCR | Native text extraction for text PDFs and PaddleOCR for images or pages without usable text |
| AI extraction | OpenRouter-backed LLM extraction into a constrained JSON structure |
| Data quality | Type checks, required-field checks, simple invoice business rules, and issue reporting |
| Review | Editable proposed values, source evidence where available, manual approval, and audit events |
| Output | Approved-record list, CSV and JSON export, and a small authenticated read API |
| Deployment | Docker-friendly local and low-cost single-host deployment documentation |

The V1 user selects “Invoice” rather than relying on automatic document classification. This keeps the first workflow predictable while preserving a clear place to add classification later.

### Future features

- Preconfigured document types for receipts, resumes, forms, and business documents.
- Additional schema versions and controlled schema migration workflows.
- User-configured schemas after the core system has proved useful.
- Document classification and routing to the right schema.
- Batch uploads and batch review queues.
- Table and line-item extraction.
- Additional languages and document-quality improvements.
- Local-LLM support through the same provider interface used by OpenRouter.
- Workspace sharing, roles, team review queues, and enterprise SSO.
- Destination connectors for spreadsheets, ERP systems, CRM systems, webhooks, and scheduled exports.
- Record amendment history, duplicate detection, analytics, quality evaluation, and model comparison.

### Features intentionally excluded from V1

- A no-code schema builder or generic workflow designer.
- Automatic approval or straight-through posting to an external system.
- Invoice line-item and table extraction.
- Multiple active LLM providers, model-routing logic, or local-model hosting.
- Automated document classification.
- Multi-tenant workspaces, complex role-based access control, SSO, or collaboration features.
- Webhooks, third-party database writes, and ERP integrations.
- Microservices, Kubernetes, a vector database, agent frameworks, and a separate message broker.

The constraint is deliberate: V1 proves that one document can become one reviewed structured record. It should not attempt to solve enterprise document automation.

## 3. System architecture

### High-level architecture

~~~mermaid
flowchart TB
    User[User] --> Web[Next.js frontend]
    Web --> API[FastAPI API]

    API --> Auth[Authentication and authorization]
    API --> DB[(PostgreSQL)]
    API --> Storage[(Private document storage)]
    API --> Jobs[Extraction jobs in PostgreSQL]

    Worker[Python background worker] --> Jobs
    Worker --> Storage
    Worker --> Process[Document processing]

    Process --> Text[Native PDF text extraction]
    Process --> OCR[PaddleOCR fallback]
    Text --> Normalize[Normalized document text and evidence]
    OCR --> Normalize

    Normalize --> Extract[LLM extraction service]
    Extract --> Router[LLM provider abstraction]
    Router --> OpenRouter[OpenRouter API]
    Router -. future adapter .-> LocalLLM[Local LLM]

    Extract --> Map[Schema mapping]
    Map --> Validate[Validation]
    Validate --> DB

    API --> Review[Review, approval, export, and read API]
    Review --> DB
~~~

Use one repository with a Next.js frontend and a Python backend. The FastAPI API and the background worker share backend modules but run as separate Docker processes. PostgreSQL holds both application data and the small V1 job queue, avoiding a Redis or broker dependency until scale requires one.

For development, private document storage can be a Docker-mounted application volume. For hosted use, the same storage interface can point to a private S3-compatible bucket or an equivalent private object store. Original documents must never be served from a public URL.

### Technology baseline

| Layer | V1 technology |
|---|---|
| Frontend | Next.js, TypeScript, and Tailwind CSS |
| Backend | FastAPI and Python |
| Database and job state | PostgreSQL |
| OCR | Native PDF text extraction with PaddleOCR fallback |
| LLM | OpenRouter API behind a provider abstraction; local LLM support is a future adapter |
| File storage | Private application volume locally; private object storage when hosted |
| Deployment | Docker Compose on a low-cost host, documented for GitHub portfolio use |

### Component responsibilities

| Component | Responsibility |
|---|---|
| Next.js frontend | TypeScript and Tailwind CSS interface for login, upload, document list, status display, review form, approved-record list, and export controls |
| FastAPI API | Authentication integration, authorization, upload validation, document metadata, review edits, approval, exports, and read API |
| PostgreSQL | User data, document metadata, schema definitions, job state, extraction results, review state, and audit history |
| Background worker | Claims jobs safely, performs processing, calls AI services, saves artifacts and results, retries recoverable failures |
| Document-processing module | Inspects files, renders pages when needed, extracts native PDF text, and prepares OCR inputs |
| OCR module | Runs PaddleOCR and returns text blocks with page and position evidence |
| Schema and validation module | Selects a schema version, maps extracted candidates, normalizes types, and enforces deterministic rules |
| LLM provider abstraction | Gives the pipeline one extraction interface while OpenRouter is used now and a local model can be added later |
| Private storage adapter | Stores originals, previews, OCR artifacts, and optional raw provider-response artifacts behind opaque keys |
| Docker deployment | Runs the frontend, API, worker, PostgreSQL, and private storage configuration with clear environment variables |

Keep these as modules within one backend codebase. Separate services are not justified for a solo-developer portfolio V1.

### Deployment shape

A low-cost deployment can run Docker Compose on one small VM:

- Next.js frontend and FastAPI API behind an HTTPS reverse proxy.
- One worker with bounded concurrency and memory limits so OCR cannot exhaust the host.
- PostgreSQL with a persistent volume and off-host backups.
- Private object storage or a persistent encrypted storage volume.
- Environment-managed secrets for the database, authentication, storage, and OpenRouter.

This design is Docker-friendly locally and gives the repository a credible path to production without claiming high availability.

## 4. Complete workflow

### End-to-end flow

~~~mermaid
flowchart LR
    A[User upload] --> B[Private file storage]
    B --> C[Document processing]
    C --> D[Native text extraction or PaddleOCR]
    D --> E[LLM information extraction]
    E --> F[Schema mapping]
    F --> G[Validation]
    G --> H[Human review when required]
    H --> I[Structured database record]
    I --> J[Export or authenticated API]
~~~

### Detailed workflow

| Step | System behavior | Result |
|---|---|---|
| 1. User upload | The API authenticates the user, verifies file type and limits, assigns the selected document type, and stores the original privately. | A document row is created with status Uploaded. |
| 2. File storage | The API saves an opaque storage key, checksum, MIME type, original filename, size, and ownership metadata. It creates an extraction job only after storage is finalized. | The document is durable and queued safely. |
| 3. Document processing | The worker claims the job with a lease, inspects the file, counts pages, and produces page previews or renderings when needed. | The job changes to Processing. |
| 4. OCR and text capture | Text PDFs use native extraction first. Image files, scans, and PDF pages with insufficient text use PaddleOCR. | A normalized page-and-block representation is stored as a private artifact. |
| 5. AI extraction | The selected schema and normalized document content are sent through the OpenRouter adapter. The LLM returns candidate values, nulls for unknown values, and evidence references in structured JSON. | A raw AI result is retained for traceability. |
| 6. Schema mapping | The backend maps candidates into the selected schema version, applies predictable type normalization, and preserves the original values and evidence. | A typed extraction draft is created. |
| 7. Validation | Schema validation and invoice rules identify missing fields, invalid dates, malformed decimals, and inconsistent totals. | The draft is marked Ready for review or Needs review, with explicit issues. |
| 8. Human review | The reviewer compares proposed data with page previews, corrects fields, and resolves required issues. V1 requires explicit approval for every record. | The reviewer saves a versioned review draft. |
| 9. Database storage | Approval revalidates the reviewed draft in one transaction. The approved mapped JSON becomes the V1 structured database record and is linked to its source document, schema, model, and review version. | The record is immutable for V1 and marked Approved. |
| 10. Export and API | The user downloads CSV or JSON, or retrieves approved records through the authenticated read API. Drafts and failed extractions are never exported as approved data. | Structured data is available for downstream use. |

### Status model

Use separate processing and review states so a technically complete AI run is never mistaken for an approved business record.

| Area | Suggested states |
|---|---|
| Document processing | Uploaded, Queued, Processing, Processed, Failed, Deleted |
| Extraction result | Draft, Needs review, Approved, Rejected, Superseded |
| Job execution | Queued, Running, Retry scheduled, Succeeded, Failed |

If a model or OCR call fails, the job records a safe error code, retries only recoverable errors within a small limit, and ultimately becomes Failed. It must not create an approved record or silently substitute invented values. A user may retry processing or enter data manually through the review path.

## 5. AI pipeline design

### OCR layer

The OCR layer produces a normalized representation that later stages can use consistently:

- PDF text extraction runs first for text-based PDFs. It is lower cost and usually preserves better reading order than OCR.
- The system evaluates whether each page has usable native text. Empty pages, scans, or poor-quality extraction trigger PaddleOCR for that page.
- JPEG and PNG uploads go directly to PaddleOCR.
- The normalized artifact stores page number, text blocks, bounding boxes when available, source method, and an OCR-quality indicator. This supports evidence links in the review screen.
- The worker stores the artifact privately so an LLM retry does not repeat expensive OCR work.

V1 should support English invoices and a small, documented file limit, such as 10 MB and 10 pages. Image rotation correction and advanced layout analysis may be added only after representative documents show a need.

### LLM layer

The LLM layer has one provider-independent responsibility: convert normalized document content into a candidate object that follows the selected extraction schema.

| Design choice | V1 decision |
|---|---|
| Provider interface | One extraction interface accepts document context, schema version, and prompt version, then returns a structured candidate result |
| Active provider | OpenRouter API with one configured model |
| Future provider | A local-LLM adapter implements the same interface without changing the worker, review UI, or database design |
| Output format | JSON-only response constrained by the requested schema; unknown fields are null rather than guessed |
| Evidence | Each candidate should include page and text-block references where the OCR representation permits it |
| Provider metadata | Save provider, model, prompt version, request timing, token use, and sanitized error data with the result |

Prompt templates are version-controlled alongside the backend. A prompt contains the selected schema, field descriptions, normalization expectations, rules for missing values, and a request for source evidence. The system records the prompt version used by each extraction so changes in prompt behavior can be compared later.

Do not build multi-model routing, autonomous tool use, conversational agents, or automatic prompt optimization in V1. One provider adapter and one evaluated model are enough to demonstrate the architecture.

### Schema mapping layer

The platform separates AI candidate fields from the stored record. A schema definition describes:

- The document type it supports.
- Field names, data types, required status, and display labels.
- Normalization rules, such as date and decimal formats.
- Validation rules and any simple mapping aliases.
- A schema version and the prompt version compatible with it.

For V1, the Invoice schema is seeded by the application and selected explicitly. Schema mapping converts the LLM candidate object into the exact invoice data shape, parses values safely, retains nulls for unresolved values, and preserves the evidence map. Future document types add schemas rather than special-purpose database tables or separate pipelines.

### Validation layer

Validation must be deterministic and run after every LLM response and again before approval.

| Validation level | Examples |
|---|---|
| Schema validation | Valid JSON shape, expected keys, required fields, strings, dates, decimals, and enumerated currency codes |
| Normalization validation | Unambiguous date parsing, decimal parsing, leading-zero preservation for identifiers, and canonical currency representation |
| Business rules | Total is non-negative, required approval fields exist, due date is not clearly before issue date, and subtotal plus tax differences are flagged for review |
| Evidence checks | Evidence references point to a real page and text block when evidence is present |
| Review checks | User edits still satisfy the selected schema and approval rules |

Validation reports issues by field and severity. It may flag a total mismatch, but it must not calculate a missing value and present it as extracted fact. Validation results guide the reviewer; they do not authorize automated approval in V1.

### Error handling and recovery

- Treat malformed model output as untrusted input. Parse it defensively, validate it, and send invalid output to a failed or reviewable state.
- Retry only transient failures such as timeouts or temporary provider errors. Use bounded retries with job leases to avoid duplicate work.
- Preserve raw provider output privately or in redacted form for debugging, alongside a safe user-facing error message.
- Save completed OCR artifacts and successful extraction checkpoints so a retry can resume work where practical.
- Make result writes idempotent. A worker that resumes after a crash must not create duplicate approved records.
- Never expose provider credentials, document text, or raw stack traces in the UI or application logs.

## 6. PostgreSQL database design

PostgreSQL is the source of truth for ownership, lifecycle state, schemas, results, review decisions, and audits. Use UUID primary keys, UTC timestamps, and JSONB only for flexible schema-driven document data.

### Core tables

| Table | Purpose and key fields |
|---|---|
| users | User ID, email or authentication subject, account status, created timestamp, and last-login metadata |
| document_types | Stable type key such as invoice, display name, description, enabled status, and created timestamp |
| schemas | Schema ID, document type ID, schema key, immutable version, JSON schema definition, mapping rules, validation rules, prompt version, status, and created timestamp |
| documents | Document ID, owner user ID, selected document type ID, selected schema ID, original filename, opaque storage key, checksum, MIME type, size, page count, processing status, created timestamp, and deleted timestamp |
| extraction_jobs | Job ID, document ID, schema ID snapshot, state, current stage, attempt count, available time, worker lease token and expiry, started and completed timestamps, and sanitized error code |
| extraction_results | Result ID, document ID, job ID, schema ID and version, result version, OCR artifact reference, provider and model metadata, prompt version, raw candidate output, mapped data, evidence map, validation issues, reviewed data, review version, reviewer ID, status, and approval timestamp |
| audit_logs | Audit ID, actor user ID, document ID, result ID when applicable, action, timestamp, request correlation ID, and redacted metadata |

The approved reviewed-data JSON in extraction_results is the V1 structured database record. This avoids creating a separate generic record store before there is evidence that one is needed. Later, target-specific record tables or connectors can be added without discarding the immutable extraction result.

### Relationships

~~~mermaid
erDiagram
    USERS ||--o{ DOCUMENTS : owns
    USERS ||--o{ EXTRACTION_RESULTS : reviews
    USERS ||--o{ AUDIT_LOGS : performs
    DOCUMENT_TYPES ||--o{ SCHEMAS : defines
    DOCUMENT_TYPES ||--o{ DOCUMENTS : categorizes
    SCHEMAS ||--o{ DOCUMENTS : selected_for
    SCHEMAS ||--o{ EXTRACTION_JOBS : snapshots
    DOCUMENTS ||--o{ EXTRACTION_JOBS : queues
    DOCUMENTS ||--o{ EXTRACTION_RESULTS : has_versions
    EXTRACTION_JOBS ||--o| EXTRACTION_RESULTS : produces
    DOCUMENTS ||--o{ AUDIT_LOGS : records
    EXTRACTION_RESULTS ||--o{ AUDIT_LOGS : traces
~~~

- One user owns many documents. V1 authorization always starts from document ownership.
- One document type has many schema versions. Invoice version 1 is the only enabled V1 schema.
- A document records the document type and schema selected at upload, while a job snapshots the schema used for that exact processing attempt.
- A document can have many jobs and many extraction-result versions because it may be reprocessed. Only the latest non-superseded result is presented for review.
- Each extraction result retains the model, prompt, schema, OCR artifact, mapped data, validation issues, and human-review decision that produced it.
- Audit logs link actions to a user and the affected document or result without copying sensitive document content.

### Version-tracking rules

1. Schema definitions are immutable once used. A changed field definition creates a new schemas row with a higher version.
2. Every extraction job references the exact schema version and prompt version it used.
3. Reprocessing a document creates a new extraction-results version; it never overwrites the original AI output.
4. Review edits increment a review version and use optimistic concurrency so one reviewer cannot silently overwrite another edit.
5. Approval stores the reviewed data with its schema and result versions. Exports retrieve only the approved version.
6. V1 does not support post-approval amendments. A correction is handled by a new processing result or replacement document until an explicit amendment feature is built.

### Data-storage choices

- Keep relational columns for ownership, lifecycle, timestamps, status, job execution, and references.
- Store schema-driven extracted fields, evidence maps, and field-level validation issues as JSONB.
- Preserve identifiers such as invoice numbers as text. Parse monetary values as precise decimals in application validation before storage.
- Add generated reporting columns or specialized relational tables only after a real query or reporting requirement proves they are necessary.
- Index document ownership and status, jobs by runnable state and available time, and results by document ID, status, and version.

## 7. Security design

### Authentication and authorization

- Use a maintained authentication solution. The frontend establishes a signed session or token, and FastAPI verifies the authenticated identity for every protected request.
- V1 uses owner-based authorization: a user can access only their own documents, previews, jobs, results, exports, and audit-relevant actions.
- Enforce ownership checks in the API layer, not only in the frontend. Never accept a user ID supplied by the client as authority.
- Keep the future authorization boundary centralized so a workspace-membership check can later replace simple ownership checks.

### Data privacy and file security

- Store originals, previews, OCR artifacts, and raw AI responses in private storage under opaque keys.
- Serve files through an authenticated API or narrowly scoped, short-lived download URL. Do not expose public buckets or guessable file paths.
- Validate file signatures and allowed MIME types, not filename extensions alone. Enforce upload size, page-count, image-dimension, parser-timeout, and worker-resource limits.
- Use malware scanning before processing if the deployed application accepts uploads from untrusted public users.
- Define retention and deletion behavior. Deleting a document should block new worker writes, remove related private artifacts on a controlled cleanup path, and preserve only legally appropriate audit metadata.
- Clearly disclose that document content is sent to the configured external LLM provider through OpenRouter. Do not use customer documents in demonstrations without authorization.

### Encryption and secrets

- Use HTTPS for browser, API, storage, and provider traffic.
- Enable encryption at rest for the database volume, backups, and hosted private storage where the hosting provider supports it.
- Keep API keys, authentication secrets, database credentials, and storage credentials in environment-managed secrets. Never place them in the repository, frontend bundle, database records, or logs.
- Encrypt off-host backups and test a restoration procedure before calling the deployment complete.

### Audit logging

Record security- and data-relevant events: login where appropriate, upload, processing retry or failure, review edit, approval, export, deletion request, and API access. Store actor, time, affected entity, and redacted context. Do not write original document contents, tokens, passwords, or raw provider prompts into routine logs.

### Safe AI-output handling

- Treat OCR text and LLM output as untrusted data, including text that tries to override instructions.
- Send document content as data within a fixed extraction prompt. Do not give the model tool access, shell access, database access, URL-fetching access, or authority to change system state.
- Accept only parsed JSON that passes server-side schema and business-rule validation.
- Never build SQL, file paths, HTML, or API actions directly from model output.
- Escape data in the UI and protect CSV exports from spreadsheet-formula injection.
- Require user approval before an extracted record becomes exportable in V1.

## 8. Agile development plan

Each sprint should end with a usable vertical slice or an observable reliability improvement. Use synthetic or authorized invoices for all development and portfolio screenshots.

| Sprint | Goal | Scope | Exit criteria |
|---|---|---|---|
| Sprint 0: Planning | Establish a testable product boundary | Invoice field definitions, approval rules, sample documents, user flow, schema versioning decision, repository layout, and deployment assumptions | A written invoice schema, sample set, acceptance criteria, and architecture diagram are agreed before implementation |
| Sprint 1: Basic upload and storage | Make private documents durable and visible | Authentication, owner checks, upload validation, private storage adapter, document metadata, list view, and processing-status placeholder | A signed-in user can upload a supported invoice and cannot retrieve another user's document |
| Sprint 2: OCR pipeline | Produce reusable document text and evidence | PostgreSQL-backed worker, job leases, native PDF text extraction, PaddleOCR fallback, artifact storage, previews, and failure status | Sample scans and text PDFs produce page-linked text or a clear recoverable failure |
| Sprint 3: LLM extraction | Produce a validated invoice draft | OpenRouter adapter, prompt templates, structured JSON parsing, invoice schema mapping, validation issues, provider metadata, and bounded retries | A sample invoice creates a draft with candidate fields, evidence, and field-level issues |
| Sprint 4: Review workflow and database integration | Turn drafts into approved records | Review form, edit versioning, approval transaction, audit events, approved-data list, CSV/JSON export, and authenticated read API | A user can correct a draft, approve it, and export only the approved structured record |
| Sprint 5: Security and deployment | Make the portfolio project safe to run and easy to evaluate | HTTPS deployment setup, environment secrets, quotas, safe logs, deletion behavior, backup and restore test, Docker Compose documentation, README, and evaluation report | A fresh environment can run the demo safely, recover from backup, and explain architecture and limitations |

### Sprint TODO checklist

#### Sprint 0

- [ ] Define the Invoice V1 schema, null behavior, required approval fields, and validation rules.
- [ ] Collect a small labeled set of synthetic or authorized invoices, including scans and text PDFs.
- [ ] Write acceptance scenarios for success, missing values, invalid values, and provider failure.
- [ ] Confirm Docker Compose, storage, authentication, and low-cost hosting choices.

#### Sprint 1

- [ ] Build authenticated upload with type, signature, size, and page-limit checks.
- [ ] Store original files privately and persist document ownership and metadata.
- [ ] Build a document list and status view.
- [ ] Verify cross-user document access is denied.

#### Sprint 2

- [ ] Add durable PostgreSQL-backed extraction jobs with leases and bounded retries.
- [ ] Add native text extraction for text PDFs.
- [ ] Add PaddleOCR fallback for scans, image uploads, and insufficient-text pages.
- [ ] Persist private OCR artifacts and page evidence for review.

#### Sprint 3

- [ ] Add the OpenRouter provider adapter with one configured model.
- [ ] Version prompts and schema contracts.
- [ ] Parse structured JSON, map it to the invoice schema, and retain source evidence.
- [ ] Add schema, normalization, business-rule, and safe error handling.

#### Sprint 4

- [ ] Build the editable review screen with document preview and field issues.
- [ ] Add optimistic edit versioning and transactional approval.
- [ ] Persist approved structured data and immutable extraction-result versions.
- [ ] Add CSV/JSON export and an authenticated approved-record read endpoint.
- [ ] Record review, approval, export, and retry events in audit logs.

#### Sprint 5

- [ ] Apply authentication, authorization, storage, rate, resource, and safe-output controls.
- [ ] Configure production secrets, HTTPS, private storage, backups, and deletion cleanup.
- [ ] Run a restore test and failure-recovery test.
- [ ] Measure extraction accuracy, review correction rate, processing time, and approximate cost per document on held-out samples.
- [ ] Publish a polished README, demo screenshots, architecture diagram, and setup instructions.

## 9. Portfolio positioning

Present the project as a reliable AI data-entry system, not as a chat interface and not as a narrowly hard-coded invoice parser. The strongest story is that the product combines AI with deterministic validation, human review, version tracking, private file handling, and a real deployment path.

### GitHub README

The README should lead with a concise outcome statement: “Convert PDFs, images, and scanned documents into reviewed, structured database records.” It should then show that V1 supports invoices while its schema-driven architecture can extend to other document types.

Include:

- A short workflow diagram from upload through approval and export.
- Screenshots or a short GIF using synthetic documents only.
- The V1 problem statement and a before-and-after example of manual entry versus reviewed structured data.
- The architecture diagram and a brief explanation of the worker, OCR fallback, LLM abstraction, validation, storage, and review boundaries.
- A feature matrix separating what works in V1 from future capabilities.
- Local Docker setup, required environment-variable names without secrets, and a safe sample-data setup.
- A sample sanitized input and resulting approved JSON or CSV.
- Evaluation metrics measured on held-out samples: field accuracy, correction rate, latency, and cost per document.
- A clear limitations section covering invoice-only V1 behavior, mandatory human approval, English scope, and external LLM data handling.

Avoid claiming production-scale automation, perfect accuracy, or enterprise compliance unless those claims have been demonstrated.

### Resume positioning

Use an outcome-oriented bullet such as:

> Built an AI data-entry automation platform with Next.js, FastAPI, PostgreSQL, PaddleOCR, and OpenRouter that converts invoice documents into validated, human-reviewed structured records with private storage, audit trails, and CSV/JSON export.

After measurement, add only verified results, for example field accuracy on a held-out synthetic set or the reduction in manual review time. The technical story should emphasize practical AI reliability: schema-constrained extraction, deterministic validation, evidence-aware review, job recovery, and secure document handling.

## 10. Final review: keep V1 achievable

### Unnecessary complexity to avoid

| Tempting addition | Why it should wait |
|---|---|
| Generic visual schema builder | It requires schema UX, migration rules, validation design, permissions, and support documentation before the core workflow is proven |
| Automatic classification | User-selected Invoice is reliable enough for V1 and avoids a second AI quality problem |
| Invoice line-item extraction | Tables, multi-page association, totals reconciliation, and review UX can become the whole project |
| Multiple LLMs and model routing | One provider interface and one evaluated OpenRouter model demonstrate the architecture |
| Local-model hosting | Hardware, inference serving, quality evaluation, and operations distract from proving the product |
| Separate queue, OCR, validation, and export services | PostgreSQL jobs and backend modules are sufficient at V1 scale |
| Workspaces and detailed RBAC | Single-user ownership demonstrates authorization without a complex collaboration product |
| Direct ERP or spreadsheet writes | CSV, JSON, and a read API prove data portability with far less integration risk |
| Auto-approval | It needs real error-rate evidence, policy rules, and a stronger exception workflow |
| Kubernetes, vector search, and agents | They do not solve the document-to-record workflow and make local evaluation harder |

### Recommended simplifications

- Implement one document type, one invoice-header schema, one language, and one review screen.
- Require human approval for every V1 result.
- Use PostgreSQL as the job queue and one Python worker with small, bounded concurrency.
- Store approved schema-driven data as JSONB in extraction results rather than designing many domain tables prematurely.
- Use one OpenRouter model behind a small adapter and define, but do not build, the local-LLM adapter.
- Use one storage adapter with a private Docker volume locally and a private object store when hosted.
- Make reprocessing explicit and append-only; defer amendment workflows after approval.
- Build export only for approved data and postpone external integrations.

### V1 definition of done

V1 is complete when a signed-in user can upload a synthetic or authorized invoice, see reliable processing status, receive an OCR- and LLM-generated extraction draft, correct it against a document preview, approve it, and retrieve the resulting structured record through CSV, JSON, or an authenticated API. The same repository must run with Docker, keep documents private, recover safely from a worker failure, and document measured limitations.

That is substantial enough for a senior-quality portfolio project while remaining feasible for one developer. Future document types should be added by creating schemas and targeted extraction rules after the invoice workflow has been evaluated, not by broadening V1 before it works.

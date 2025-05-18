# Migrations & Scalability - DataFlow AI

> This document details the migration and scalability strategy (MinIO, Temporal, Supabase) for DataFlow AI.

## 1. Current Architecture

- **FastAPI Backend**: Orchestrates PDF extraction jobs (upload, extraction, rasterization, AI analysis, report generation)
- **MinIO Object Storage**: All files (PDFs, results, logs, progress.json) are stored in an S3-compatible bucket, local or cloud
- **FileStorage Abstraction**: All storage access logic goes through a single Python service (`FileStorage`), making it easy to swap backends (local, MinIO, Supabase, S3...)
- **Progress Feedback**: Each job writes a `progress.json` file updated at every key step (init, extraction, raster, upload, clean, success/failed), accessible by the frontend
- **Automatic Cleanup**: After upload to MinIO, local files are deleted to avoid disk saturation

## 2. Technical Choices & Migration Readiness

- **Why MinIO?**
  - Fast deployment, zero external dependencies, perfect for dev/test/local
  - S3-compatible: access logic is the same as in production (AWS S3, Supabase Storage...)
  - Lets you validate the whole chain (upload, download, clean, feedback) without cloud costs

- **Preparing for Temporal**
  - All business logic is factored into pure functions/services (no dependency on the orchestrator)
  - Orchestration (job management, retries, monitoring) is separated from business logic
  - API endpoints only trigger jobs, no heavy business logic inside
  - File access is abstracted: Temporal can orchestrate workers without changing business code

- **Preparing for Supabase Storage**
  - The FileStorage abstraction allows you to implement a Supabase backend (REST API or S3-compatible) without touching the rest of the code
  - Auth, fine-grained access control, and frontend integration will be handled by Supabase in production

## 3. Migration Steps: Temporal & Supabase

- **Temporal**
  1. Deploy a Temporal cluster (or use Temporal Cloud)
  2. Implement workflows/activities that call the existing business functions (extraction, raster, upload...)
  3. Adapt the API to trigger Temporal workflows instead of running jobs locally
  4. Keep the same storage interface (FileStorage)

- **Supabase Storage**
  1. Create a Python backend for FileStorage using Supabase's REST API or S3 interface
  2. Change the config/env to point to Supabase
  3. Auth and access control are managed by Supabase (JWT, ACL, etc.)

## 4. Production Caveats

- Always upload progress.json to the storage backend before deleting local files
- Never expose MinIO without a reverse proxy/auth in production (prefer Supabase or S3)
- Monitor RAM/CPU if running multiple heavy jobs in parallel
- Use a separate bucket per environment (dev, staging, prod)

## 5. Workflow Diagram (text)

1. User uploads a PDF via the frontend
2. The API saves the PDF to the storage backend (MinIO or other)
3. The API triggers an extraction job (classic + raster)
4. Each job step updates progress.json (init, extraction, raster, upload, clean, success/failed)
5. Results (JSON, ZIP, reports) are uploaded to the storage backend
6. Local files are cleaned up
7. The frontend queries the API to track progress and retrieve results

---

**This document is up to date with the current logic and anticipates migration to Temporal and Supabase.**
For any questions or adaptation, see the `FileStorage` service and the `.env` config. 
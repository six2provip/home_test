# OptiBot — OptiSigns → OpenAI Vector Store Sync

A Python CLI application that downloads articles from the **OptiSigns Help Center**, converts them to clean Markdown, and synchronizes them with an **OpenAI Vector Store** for AI-powered retrieval (e.g., OpenAI Assistants File Search).

The application runs as a **one-shot process**: scrape → compare → upload → exit. It is designed to be run on a schedule (cron, scheduler, Docker Compose loop) to keep the vector store in sync with the live help center.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Workflow Diagram](#workflow-diagram)
- [Delta Detection — The Four Scenarios](#delta-detection--the-four-scenarios)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Usage](#usage)
  - [Docker Compose (easiest)](#docker-compose-easiest)
  - [Docker only](#docker-only)
  - [Direct Python](#direct-python)
  - [Helper script](#helper-script)
- [Scheduled Runs](#scheduled-runs)
- [Architecture](#architecture)
- [Operating Mechanism — Deep Dive](#operating-mechanism--deep-dive)
  - [Phase 1: Scrape](#phase-1-scrape)
  - [Phase 2: Sync (Delta Detection)](#phase-2-sync-delta-detection)
  - [Phase 3: Upload](#phase-3-upload)
  - [Phase 4: Cleanup & State Persistence](#phase-4-cleanup--state-persistence)
- [State File](#state-file)
- [Logging](#logging)
- [Chunking Strategy](#chunking-strategy)
- [Testing the Pipeline](#testing-the-pipeline)
- [Troubleshooting Common Scenarios](#troubleshooting-common-scenarios)

---

## How It Works

```
OptiSigns Help Center
        │
        ▼
  1. SCRAPE ─── Fetch all articles via paginated API
        │         Convert HTML → Markdown
        │         Save .md files to disk
        ▼
  2. SYNC ───── Hash each document (SHA-256)
        │         Compare against saved state
        │         Classify: added / updated / skipped / removed
        ▼
  3. UPLOAD ─── Phase 1: Upload new/updated files to OpenAI
        │         Create file batches (no polling)
        │       Phase 2: Poll all batches concurrently
        │       Phase 3: Delete old OpenAI files for updated articles
        ▼
  4. CLEANUP ── Delete OpenAI files + markdown files for removed articles
        │         Merge state (add/update entries, remove deleted)
        │         Save state & write log
        ▼
     Done (exit)
```

At **every run**, the entire pipeline executes from start to finish. The sync step ensures only the delta (what actually changed) is uploaded — unchanged articles are skipped instantly with no API cost.

---

## Delta Detection — The Four Scenarios

The application compares the current scrape against the **previous sync state** (stored in `data/state/state.json`). Each article falls into exactly one category:

| Scenario | Condition | What Happens |
|---|---|---|
| **🆕 Added** | Article exists in scraped data but **not** in saved state | Upload new file to OpenAI. Save its `file_id` in state. |
| **✏️ Updated** | Article exists in **both** places, but the hash differs (content changed) | Upload new file. After successful upload, **delete old file** from OpenAI (vector store + file object). Save new `file_id` in state. |
| **⏭️ Skipped** | Article exists in **both** places and the hash matches (no change) | Do nothing. State entry preserved as-is. |
| **🗑️ Removed** | Article exists in saved state but **not** in scraped data (deleted from source) | After successful upload of other articles: **delete file** from OpenAI, **delete markdown file** from disk, **remove** entry from state. |

**Why "removed" is handled after upload:** This guarantees that if the upload of new/updated articles fails partway through, the removed articles are not prematurely deleted — leaving the vector store in a consistent state.

---

## Project Structure

```
optibot/
├── app/
│   ├── config/
│   │   ├── constants.py        # Shared constants
│   │   └── settings.py         # Env var loading via python-dotenv
│   │
│   ├── domain/                 # Pure dataclasses — no I/O, no HTTP
│   │   ├── article.py          # Article dataclass
│   │   ├── markdown.py         # MarkdownDocument dataclass (renders to string)
│   │   └── sync_result.py      # SyncResult — holds added/updated/skipped/removed
│   │
│   ├── infrastructure/         # Adapters for external systems & storage
│   │   ├── converter/
│   │   │   └── markdown_converter.py   # HTML → Markdown via markdownify
│   │   ├── openai/
│   │   │   └── vector_store_service.py # OpenAI SDK client (upload, poll, delete)
│   │   ├── optisigns/
│   │   │   ├── article_api.py          # OptiSigns Help Center paginated API
│   │   │   ├── client.py               # HTTP client (requests)
│   │   │   └── incremental_api.py      # Incremental fetch (future use)
│   │   └── storage/
│   │       ├── log_repository.py       # JSON-lines log persistence
│   │       ├── markdown_repository.py  # Save/load .md files
│   │       └── state_repository.py     # Read/write sync state JSON
│   │
│   ├── services/               # Business logic — coordinates infrastructure
│   │   ├── scrape_service.py   # Orchestrates article fetch + conversion + save
│   │   ├── sync_service.py     # Hash comparison + delta classification
│   │   └── upload_service.py   # Two-phase upload + concurrent polling + cleanup
│   │
│   ├── utils/                  # Small reusable helpers
│   │   ├── file.py
│   │   ├── hash.py             # SHA-256 hashing
│   │   ├── logger.py           # Logging setup
│   │   ├── slug.py
│   │   ├── json_utils.py       # JSON read/write helpers
│   │   ├── text.py             # Text normalization
│   │   ├── url.py              # URL parsing
│   │   └── env.py              # Required env var validation
│   │
│   └── main.py                 # Entry point — orchestrates the full pipeline
│
├── data/                       # Runtime data (persisted across runs)
│   ├── markdown/               # .md files — one per article
│   ├── state/                  # state.json — sync tracking state
│   └── logs/                   # sync.log — JSON-lines log
│
├── tests/                      # (No unit tests yet — tested via integration)
├── docker-compose.yml          # Docker Compose config
├── Dockerfile                  # Container image
├── prompt.md                   # Original implementation specification
├── JSON_EXEMPLE.json           # Sample API response
├── requirements.txt            # Python dependencies
├── run.sh                      # Helper shell script (Linux/macOS)
└── README.md                   # This file
```

---

## Prerequisites

You only need **one thing installed locally**:

- **[Docker](https://docs.docker.com/get-docker/)** (includes Docker Compose)

That's it. No Python, no pip, no virtual environment needed on your machine when using Docker.

You will also need:

- An **OpenAI API key** with access to [Vector Stores](https://platform.openai.com/docs/assistants/tools/file-search)
- A pre-created **OpenAI Vector Store** ID
- An **OpenAI Assistant** ID (for future use; required at startup)

---

## Setup

### 1. Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
OPENAI_VECTOR_STORE_ID=vs_...
OPENAI_ASSISTANT_ID=asst_...
OPTISIGNS_BASE_URL=https://support.optisigns.com
MARKDOWN_DIR=data/markdown
STATE_FILE=data/state/state.json
LOG_FILE=data/logs/sync.log
```

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key (must have vector store write access) |
| `OPENAI_VECTOR_STORE_ID` | Target vector store ID to upload files into |
| `OPENAI_ASSISTANT_ID` | Assistant ID (reserved for future use; required at startup) |
| `OPTISIGNS_BASE_URL` | OptiSigns Help Center base URL (e.g., `https://support.optisigns.com`) |
| `MARKDOWN_DIR` | Directory to store converted markdown files |
| `STATE_FILE` | Path to the JSON file that tracks sync state per article |
| `LOG_FILE` | Path to the JSON-lines sync log |

### 2. Create the data directories

```bash
mkdir -p data/markdown data/state data/logs
```

### 3. (Optional) Bootstrap OpenAI resources

If you haven't created a vector store yet:

```bash
# Create a vector store
curl https://api.openai.com/v1/vector_stores \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "OptiSigns Help Center"}'
```

---

## Usage

### Docker Compose (easiest — no Python required)

```bash
docker compose up --build
```

Docker Compose will:
1. Build the image (all Python dependencies install inside the container)
2. Load environment variables from `.env`
3. Mount the `./data` folder so markdown files, state, and logs persist on your machine
4. Run the full sync pipeline and exit

> **No Python on your machine? No problem. Docker has Python inside the container.**

### Docker only

```bash
docker build -t optibot .
docker run --rm \
  --env-file .env \
  -v "$(pwd)/data:/app/data" \
  optibot
```

### Direct Python (requires Python 3.12+ locally)

```bash
pip install -r requirements.txt
python -m app.main
```

### Helper script (Linux/macOS, requires Python 3.12+ locally)

```bash
chmod +x run.sh
./run.sh
```

The helper script loads `.env`, verifies required variables, creates a virtual environment if needed, installs dependencies, and runs the application.

---

## Scheduled Runs

Wrap the Docker Compose command in a cron job or scheduler to keep the vector store in sync periodically.

### Linux cron (every hour)

```bash
0 * * * * cd /path/to/optibot && docker compose up --build
```

### Docker Compose with restart loop

Uncomment the `restart` and `command` lines in `docker-compose.yml`:

```yaml
services:
  optibot:
    build: .
    container_name: optibot
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    command: >
      sh -c "while true; do python -m app.main; sleep 3600; done"
```

This runs the sync every hour in a loop within the same container.

### Windows Task Scheduler

1. Open **Task Scheduler**
2. Create a new task
3. Trigger: Daily, repeat every 1 hour
4. Action: Start a program → `docker-compose up --build` in the project directory

---

## Architecture

The project follows **Clean Architecture** principles with a strict inward dependency flow:

```
   ┌────────────────────────────────────────────────┐
   │                   Config                       │
   │  (env vars, constants — loaded at startup)      │
   └────────────────────────────────────────────────┘
                          │
   ┌────────────────────────────────────────────────┐
   │                 Services                       │
   │  (business logic, orchestrates infrastructure) │
   │  ScrapeService · SyncService · UploadService   │
   └────────────────────────────────────────────────┘
                          │
   ┌────────────────────────────────────────────────┐
   │              Infrastructure                    │
   │  (external adapters — OptiSigns, OpenAI,       │
   │   MarkdownConverter, file storage)             │
   └────────────────────────────────────────────────┘
                          │
   ┌────────────────────────────────────────────────┐
   │                 Domain                         │
   │  (pure dataclasses — no I/O, no HTTP)          │
   │  Article · MarkdownDocument · SyncResult       │
   └────────────────────────────────────────────────┘
   ┌────────────────────────────────────────────────┐
   │                 Utils                          │
   │  (small reusable helpers — hash, text, url)    │
   └────────────────────────────────────────────────┘
```

Dependencies flow **inward**: `Services → Infrastructure → Domain`. The Domain layer knows nothing about the outside world.

---

## Operating Mechanism — Deep Dive

### Phase 1: Scrape

**`ScrapeService.scrape()`**

1. Calls `ArticleAPI.get_all()` which fetches articles from the OptiSigns Help Center API using paginated requests (`next_page` until `null`).
2. For each article, `MarkdownConverter.convert()` transforms the HTML `body` into clean Markdown using `markdownify`.
3. Each converted document is saved to disk as `{article_id}.md` via `MarkdownRepository.save()`.
4. Returns a list of `MarkdownDocument` objects (title, content, URL, ID, updated_at).

**Output:** Markdown files on disk + in-memory list of documents.

**No authentication required** — the OptiSigns Help Center API is public.

### Phase 2: Sync (Delta Detection)

**`SyncService.compare(documents)`**

1. Loads the previous sync state from `state.json` (a dict of `{article_id: {hash, file_id}}`).
2. For each scraped document, computes a SHA-256 hash of the rendered markdown content.
3. Classifies each article:

```
                   ┌──────────────────────┐
                   │  Article in scraped?  │
                   └──────────────────────┘
                          │        │
                       Yes        No
                          │        │
                          ▼        ▼
              ┌─────────────────┐   ┌──────────────────────┐
              │ In saved state? │   │   REMOVED            │
              └─────────────────┘   │ (state entry exists  │
                │           │       │  but article gone    │
              Yes          No       │  from source)        │
                │           │       └──────────────────────┘
                ▼           ▼
      ┌────────────────┐  ┌──────┐
      │ Hash matches?  │  │ADDED │
      └────────────────┘  └──────┘
        │           │
      Yes          No
        │           │
        ▼           ▼
    ┌────────┐  ┌─────────┐
    │SKIPPED │  │UPDATED  │
    └────────┘  └─────────┘
```

4. Returns a `SyncResult` with four lists: `added`, `updated`, `skipped`, `removed`.

**Key detail — hash computation:** The hash is computed from the **rendered markdown string** (not the raw HTML), which includes:
```
# {title}

{content}

---

Article URL:
{html_url}

Article ID:
{id}

Last Updated:
{updated_at}
```

Any change to title, body content, URL, or last-updated timestamp produces a different hash and triggers an update.

### Phase 3: Upload

**`UploadService.upload(sync_result)`**

This is the most sophisticated phase and uses a **three-stage process**:

#### Stage 1: Upload all files (no polling)

For each batch of 30 files (configurable via `batch_size`):

1. Upload each file to OpenAI via `POST /v1/files` (purpose: `assistants`)
2. Create a file batch: `POST /v1/vector_stores/{id}/file_batches`
3. Store the `batch_id` and returned `file_ids`

All batches are created in sequence. No polling happens yet — this stage is fast because it only uploads and creates batches.

#### Stage 2: Poll all batches concurrently (ThreadPoolExecutor)

All batch polling is submitted to a **`ThreadPoolExecutor`** in parallel. As each batch completes (or times out after 300s), its status is recorded:

- **`completed`** — Files were successfully added to the vector store
- **`timeout`** — Files were uploaded but didn't finish processing in time (still treated as successful — they'll complete on OpenAI's side)
- **`failed`** — The batch errored

Concurrent polling means the total Phase 3 time ≈ time of the **slowest batch**, not the sum of all batches.

#### Stage 3: Delete old files (only for updated articles)

For every article classified as **updated**, the old OpenAI file (tracked via `file_id` in the state) is:

1. **Removed from the vector store** via `client.vector_stores.files.delete()`
2. **Deleted as a file object** via `client.files.delete()` to free storage quota

Failures here are logged as warnings but do not fail the overall run — the deletion is a cleanup operation, not a critical path.

### Phase 4: Cleanup & State Persistence

#### Removed article cleanup

After the upload phase succeeds, articles classified as **removed** are cleaned up:

1. **OpenAI cleanup:** Delete the file from the vector store + delete the file object (same two-step process as updates)
2. **Disk cleanup:** Delete the `{article_id}.md` markdown file
3. **State cleanup:** Remove the article's entry from the state dict

This happens **after** the upload to ensure that if the upload fails, removed articles are not prematurely deleted.

#### State merge

The state file is updated through a **merge** operation:

```python
state = existing_state
state.update({
    str(article_id): {
        "hash": new_hash,
        "file_id": new_file_id,   # only if upload succeeded
    }
    for each added/updated article
    if upload succeeded
})
# removed articles already popped
state_repository.save(state)
```

**Why merge instead of replace?** Previously, the state was rebuilt from scratch using only `added` + `updated` articles. This caused a bug where a run with only `skipped` articles would save an **empty state**, and the next run would re-upload everything. The merge preserves skipped and unchanged entries.

---

## State File

The state file (`state.json`) is the core of the delta detection system. Each entry maps an article ID to its last-known hash and OpenAI file ID:

```json
{
  "360049919933": {
    "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "file_id": "file-abc123"
  },
  "360050244454": {
    "hash": "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a",
    "file_id": "file-def456"
  }
}
```

| Field | Description |
|---|---|
| `hash` | SHA-256 hash of the rendered markdown content (used for change detection) |
| `file_id` | OpenAI file ID (used for cleanup when articles are updated or removed) |

The `file_id` field was added later for cleanup support. Older state entries may not have it — the code handles this gracefully by skipping OpenAI deletion when `file_id` is missing.

---

## Logging

After each sync cycle, the application appends a JSON entry to the log file configured via `LOG_FILE`.

### Log entry format

```json
{
  "status": "success",
  "added": 5,
  "updated": 2,
  "skipped": 397,
  "removed": 0,
  "upload": {
    "status": "completed",
    "batches": [
      {
        "batch_id": "vsfb_...",
        "status": "completed",
        "file_counts": {
          "in_progress": 0,
          "completed": 7,
          "failed": 0,
          "cancelled": 0,
          "total": 7
        }
      }
    ],
    "total_files": 7,
    "uploaded": 7,
    "successful_article_ids": [360049919933, ...],
    "file_ids": {"360049919933": "file-abc123", ...}
  }
}
```

| Field | Description |
|---|---|
| `status` | Overall outcome: `"success"` or if an exception occurred |
| `added` | Number of new articles uploaded |
| `updated` | Number of updated articles re-uploaded |
| `skipped` | Number of unchanged articles skipped |
| `removed` | Number of articles deleted from the source and cleaned up |
| `upload.status` | `"completed"` if all batches succeeded, `"partial"` if some failed |
| `upload.batches[].file_counts` | File-level counts from OpenAI (not chunk counts) |

### Reading logs

Each run appends one line. You can inspect the log with standard JSON-lines tools:

```bash
# View the last run
tail -1 data/logs/sync.log | python -m json.tool

# Count total runs
wc -l data/logs/sync.log

# Find runs with errors
findstr "error" data/logs/sync.log
```

---

## Chunking Strategy

This project relies on **OpenAI's automatic server-side chunking** — no custom chunking logic is implemented.

When files are uploaded via `file_batches.create()`, OpenAI automatically:
- Splits each markdown file into chunks (default chunk size: ~800 tokens).
- Generates embeddings for each chunk using the `text-embedding-3-large` model.
- Indexes the chunks in the vector store for File Search retrieval.

There is no manual chunk size or overlap configuration because OpenAI's File Search tool handles this transparently. The chunking parameters cannot be customized via the SDK — they are managed entirely by OpenAI's infrastructure.

**File counts vs. chunk counts:** The OpenAI Vector Store API exposes **file-level** counts (e.g., `total`, `completed`, `failed` files). It does **not** expose per-document chunk counts — the chunking, embedding, and indexing happen server-side and are opaque to the caller.

---

## Testing the Pipeline

### Quick health check (no modifications needed)

```bash
# Count articles from the source API
python -c "
from app.config.settings import Settings
from app.infrastructure.optisigns.article_api import ArticleAPI
from app.infrastructure.optisigns.client import OptiSignsClient
s = Settings()
api = ArticleAPI(OptiSignsClient(s))
articles = api.get_all()
print(f'API has {len(articles)} articles')
"

# Count markdown files on disk
dir /b data\markdown\*.md | find /c /v ""

# Count state entries
python -c "
from app.infrastructure.storage.state_repository import StateRepository
from app.config.settings import Settings
s = Settings()
state = StateRepository(s.STATE_FILE).load()
print(f'State has {len(state)} entries')
"
```

All three counts should match. If they don't, investigate before running the pipeline.

### Full pipeline integration test

```bash
python -m app.main
```

Expected output for a stable system:
```
INFO Loaded settings
INFO Scraped 404 articles
INFO Delta summary: added=0 updated=0 skipped=404 removed=0
INFO Upload summary: {'status': 'skipped', ...}
INFO Saved sync state for 404 articles
INFO Wrote logs
```

### Simulating scenarios for testing

| What you want to test | How to simulate | Expected delta |
|---|---|---|
| **Added** | Remove one entry from `state.json`, then run | `added=1` |
| **Updated** | Change one hash in `state.json` to garbage, then run | `updated=1` |
| **Skipped** | Normal run with no changes | `skipped=404` |
| **Removed** | Delete one `.md` file and its state entry (it won't appear as "removed" — instead delete a state entry only to test "added"; to test "removed" you'd need to simulate a deleted source article by temporarily filtering it in the API) | `removed=1` |

---

## Troubleshooting Common Scenarios

### "articles were skipped first run, then re-added on next run" (state loss bug)

**Root cause:** The previous state was overwritten with an empty dict when all articles were skipped.

**Fix applied:** State is now **merged** (existing entries are preserved). Running the pipeline again will correctly skip previously tracked articles.

### "Batch upload timed out"

Each batch has a 300-second timeout. With concurrent polling (Phase 2), the total wait time ≈ max(batch_time), not sum(batch_times). If a batch consistently times out, check:
- OpenAI service status
- File sizes (very large markdown files take longer to process)
- Network latency to the OpenAI API

### "'Beta' object has no attribute 'vector_stores'"

**Root cause:** The SDK path used `.beta.vector_stores.files.delete()` but the installed SDK version has `vector_stores` directly on the client.

**Fix applied:** Changed to `client.vector_stores.files.delete()` — matching how `file_batches.create()` and `file_batches.retrieve()` are already called.

### "Old file deletion logged a warning but didn't fail the run"

Deletion of old files (for updated or removed articles) is a **non-critical cleanup operation**. Failures are logged as warnings but do not prevent the pipeline from completing. The new files are already in the vector store; the deletion is just housekeeping.

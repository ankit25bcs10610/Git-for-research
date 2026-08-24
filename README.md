# Git for Research

Git for Research is a platform that treats research artifacts, including
documents, LLM chat exports, PDFs, and codebases, as versioned objects. It
provides git-like commit, diff, branch, and merge operations over these
artifacts, layers a CRDT-backed concurrent editing surface on top for live
collaboration, and exposes a local embedding-backed retrieval and query
surface so researchers can search across everything they have ingested,
with every result tied back to the exact artifact and commit it came from.

## Architecture

- **Artifact model and storage**: research artifacts (markdown docs, ChatGPT
  and Claude exports, PDFs, codebases) are normalized into a common versioned
  object model backed by Postgres, with codebase artifacts additionally
  tracked through pygit2 and structurally parsed with tree-sitter.
- **Commit, diff, branch, and merge engine**: a git-like layer that produces
  commits and paragraph or chunk level diffs, supports branching per
  artifact, and detects merge conflicts when overlapping regions are edited
  independently on two branches.
- **CRDT-backed concurrent editing layer**: a Node.js y-websocket relay that
  lets multiple mock users edit the same artifact concurrently, with changes
  eventually reconciled into the commit history via a snapshot bridge.
- **Ingestion pipeline**: parsers that accept markdown documents, ChatGPT and
  Claude export JSON, PDFs, and codebases, normalize them into artifacts, and
  chunk them for downstream retrieval.
- **Retrieval and embeddings**: local sentence-transformers embeddings stored
  and queried through pgvector, with no external embedding API dependency.
- **Query and chat surface**: a search module returning ranked chunks with
  provenance (artifact id, commit ref, score), consumed by a React search
  panel.
- **Frontend**: a React and TypeScript (Vite) application providing an
  artifact list view, diff views, branch and merge controls, live-editing
  and presence indicators, and the search and chat panel described above.

## How to run it

```bash
docker compose up --build
```

Once all services report healthy (postgres, backend, crdt-relay, frontend),
run the end to end smoke test from a separate terminal:

```bash
python scripts/e2e_smoke.py
# or, using the backend's existing virtualenv, which already has `requests`:
backend/.venv/bin/python scripts/e2e_smoke.py
```

The frontend is served at http://localhost:5173, the backend API at
http://localhost:8000, and the CRDT relay at ws://localhost:1234.

**Important caveat, read before trying this**: `docker compose up --build`
was **not** run in the sandbox this project was built in (no Docker was
available there; a local Postgres 15 + pgvector install was used for all
backend testing instead), and the FastAPI HTTP route layer the smoke test
calls (`/api/artifacts/ingest/*`, `/api/artifacts/{id}/branches`,
`/api/artifacts/{id}/commits`, `/api/artifacts/{id}/merge-requests`,
`/api/search`, etc.) has not been built yet — see "What wasn't completed"
below. Today, running `scripts/e2e_smoke.py` against a freshly built stack
will fail immediately at the markdown ingest step with a 404, because
`backend/app/main.py` only defines `GET /health`. This was verified by hand
during this task: a bare `uvicorn app.main:app` returns `200` for `/health`
and `404` for `POST /api/artifacts/ingest/markdown`. The script is included
because it pins down the intended contract for that route layer precisely,
and becomes a real, runnable check the moment those routes exist.

**To see the engine actually work today, without the route layer**, run:

```bash
backend/.venv/bin/python scripts/demo.py
```

against the same local Postgres+pgvector instance the test suite uses. This
calls the built Python modules directly (no HTTP) and walks through the
full story end to end: ingest a markdown doc and a ChatGPT export, branch
and make conflicting edits to the same paragraph, show a live semantic
diff, open a merge request and print the live merge conflict it detects,
resolve it and confirm the result is a real two-parent merge commit (not a
linear rewrite), have a fake "LLM agent" (an injected callable, no external
API) open its own branch and submit a merge request for human review,
chunk and embed everything with local sentence-transformers, answer a
natural-language question via pgvector similarity search, and record and
walk a provenance edge from the answer back to its source. Every step
asserts on the real result rather than just printing it, so a failure
anywhere raises an `AssertionError` instead of silently reporting success.

## What was completed versus not

Every module below was built with real, passing automated tests
(no network egress and no hosted LLM calls anywhere in the test suite):

- **Backend**: 76 pytest tests passing (`backend/.venv/bin/python -m pytest`),
  covering ingestion (markdown, ChatGPT, Claude, PDF, codebase/zip,
  codebase/git), the versioning DAG store, diff engine, structural code diff,
  git adapter, merge engine and conflict detection, collaboration (agent
  editor, merge requests), CRDT last-seen/snapshot-bridge logic, and
  retrieval (chunking, embeddings, provenance, similarity search).
- **crdt-relay**: 2 Node test-runner tests passing (`npm test` in
  `crdt-relay/`), covering multi-client Yjs sync over the websocket relay and
  the snapshot HTTP endpoint.
- **Frontend**: 14 Vitest tests passing across 9 files (`npx vitest run` in
  `frontend/`), covering the API client (`fetchArtifacts`, `fetchDiff`,
  `fetchMergeRequest`, `submitResolution`, `searchQuery`), `ArtifactList`,
  `WorkspaceView`, `DiffView`, `ConflictResolutionView`, `LiveEditor`,
  `PresenceIndicator`, `SearchChatPanel`, and `App` itself.
- **Frontend composition**: `App.tsx` now renders `WorkspaceView` (against a
  placeholder `"demo-workspace"` id, since there is no auth or
  workspace-selection UI in scope) and `SearchChatPanel` beneath the existing
  heading, so the artifact list and search are both reachable from a single
  page load. This wiring was added as a controller-directed addition on top
  of the plan's two literal task briefs, since without it none of the
  frontend built across the whole plan was reachable from the running app.

Mandatory pillars, and their actual status:

- [x] Versioned artifact model with commit, diff, branch, and merge across
      markdown docs, ChatGPT/Claude exports, PDFs, and codebases — built and
      tested as backend Python modules.
- [x] CRDT-backed concurrent editing layer via a Node.js y-websocket relay —
      built and tested; see the two caveats below about what isn't wired
      into the container yet.
- [x] Local, offline embedding and retrieval pipeline using
      sentence-transformers and pgvector, with no external LLM dependency —
      built and tested as backend Python modules (`index_chunks`,
      `similarity_search`).
- [x] Search and chat surface in the frontend backed by the retrieval API,
      with provenance shown on every result — `SearchChatPanel` is built,
      tested, and wired into `App.tsx`; it calls `searchQuery`, which hits
      `GET /api/search` — a route that does not exist on the backend yet
      (see below).

Stretch goals (not attempted, as originally scoped):

- [ ] Tree-sitter driven structural diffing of codebase artifacts beyond
      line-level diffs (note: tree-sitter based function-level diffing of a
      single file's before/after state *is* built and tested in
      `backend/app/versioning/code_diff.py` — the stretch goal not attempted
      is extending that across a whole codebase artifact's merge flow)
- [ ] Automatic conflict resolution suggestions surfaced in the merge UI
- [ ] Production-grade OCR support for scanned PDF artifacts

## What wasn't completed

This is the honest gap list, checked by hand against the code rather than
assumed from the plan:

1. **No FastAPI HTTP route layer.** `backend/app/main.py` defines only
   `GET /health`. All the ingestion, versioning, collaboration, and
   retrieval logic the plan's later tasks describe as consumed by
   `scripts/e2e_smoke.py` and by the frontend's `client.ts` exists and is
   tested as plain Python modules/functions, but nothing maps HTTP
   endpoints onto them yet. Building that route layer was explicitly ruled
   out of scope for this final task by the controller running this plan
   (a real FastAPI app wiring ~10 endpoints, request/response schemas, and
   error handling is substantial, separate work), so it is called out here
   rather than silently left implied by a "done" checkbox above.
2. **No database schema creation/migration step outside the test suite.**
   The only place `Base.metadata.create_all(engine)` is called anywhere in
   this repo is inside `backend/tests/test_db_models.py`. There is no
   startup hook in `app/main.py` and no Alembic (or equivalent) migration
   that creates tables against a fresh database. Even once the route layer
   above is built, a brand new `docker compose up` volume would need this
   before any endpoint that touches the database would work.
3. **The crdt-relay container only runs the websocket relay, not the
   snapshot bridge's HTTP endpoint.** `crdt-relay/relay.test.js` (which
   passes) requires both `./server` (the y-websocket relay on `PORT`) and
   `./snapshot` (an HTTP endpoint on `SNAPSHOT_PORT` that reads back a
   room's current text). But `crdt-relay/Dockerfile`'s `CMD` only runs
   `node server.js`, and only copies `server.js` into the image — `snapshot.js`
   and `docs.js` are never copied in or started. So in the compose stack as
   it stands, live-edit snapshots have no HTTP path back into
   `backend/app/crdt/snapshot_bridge.py`'s `commit_snapshot`. Fixing this
   was judged out of scope for this task (it touches an earlier task's
   Dockerfile/service, not the docker-compose/e2e/README work this task
   covers) and is called out here instead of silently glossed over.
4. **`docker compose up --build` was never actually run.** No Docker was
   available in the sandbox this was built in. `docker-compose.yml` and the
   three services' Dockerfiles are believed correct by inspection (image
   names, ports, env vars, build contexts were all cross-checked against the
   code that reads them — see the two corrections below — as far as that's
   possible without a daemon to actually build and run them), but this has
   not been verified by an actual run.
5. **Frontend navigation is minimal by design.** `App.tsx` renders
   `WorkspaceView` and `SearchChatPanel` so the artifact list and search are
   reachable, but `DiffView`, `ConflictResolutionView`, `LiveEditor`, and
   `PresenceIndicator` are not wired in. Each of those needs per-artifact
   routing/selection state (which diff, which merge request, which live
   session) that a single flat `App.tsx` composition can't reasonably hold
   without a router — building that was explicitly out of scope for this
   integration step. See "What would be built next" below.
6. **Chunking and indexing have no production callers.** `index_chunks`,
   `chunk_prose`, `chunk_messages`, `chunk_code`, and `add_provenance_edge`
   are all fully built and tested (`backend/app/retrieval/`), but nothing in
   this repo calls them after ingestion or after a commit lands. Even once
   the FastAPI route layer above exists, semantic search has no data to
   search until something wires ingestion/commit events to these functions.
   (`scripts/demo.py` calls all of these directly and proves they work
   correctly in isolation — the gap is specifically the missing production
   *wiring*, not the functions themselves.)
7. **The `Artifact` table is never populated.** `app/db/models.py` defines
   `Artifact`, but no code anywhere creates an `Artifact` row — every
   `artifact_id` used throughout the versioning, collaboration, and
   retrieval modules is invented ad hoc by whatever test or caller needs
   one, not looked up from this table. An artifact browser built against
   this table has no data source to list from today.
8. **PDF-ingested content has no working tokenizer path.** The PDF parser's
   JSON output has no blank lines, so `tokenize_paragraphs` run on it
   returns a single token for the whole document, and `tokenize_messages`
   raises a `KeyError` on it outright. PDFs can be committed through the
   versioning layer, but they cannot be meaningfully diffed, merged, or
   chunked today — only markdown and chat-export content can.
9. **Live-editing presence never actually broadcasts.** Nothing in the
   CRDT/live-editing code calls Yjs awareness's `setLocalStateField`, so
   `PresenceIndicator` always renders zero users, even with two genuinely
   connected, syncing clients editing the same document.

Two corrections made to the plan's brief while finalizing `docker-compose.yml`
(both verified against the actual code, not assumed):

- The brief set `RELAY_PORT: "1234"` on the `crdt-relay` service, but
  `crdt-relay/server.js` reads `process.env.PORT` (defaulting to `1234` if
  unset) — `RELAY_PORT` would have been silently ignored and only worked by
  coincidence of matching the default. Changed to `PORT: "1234"`.
- The brief's finalized `postgres` service dropped the volume mount that
  runs `backend/app/db/init.sql` (`CREATE EXTENSION IF NOT EXISTS vector;`)
  on first boot, which was present in the pre-existing skeleton. Nothing in
  the application code creates that extension itself, so a fresh
  `gfr-postgres-data` volume without it would never be able to store
  embeddings. Restored the mount.

## What would be built next

In priority order:

1. The FastAPI route layer wiring the existing, tested ingestion,
   versioning, collaboration, and retrieval modules to real HTTP endpoints,
   plus a startup-time (or Alembic) schema creation step — together these
   are what would take this from "every module works in isolation" to "the
   docker compose stack and `scripts/e2e_smoke.py` actually pass."
2. Wiring `crdt-relay`'s snapshot HTTP endpoint into the same running
   process as the websocket relay (or as a second container) and calling it
   from the new route layer's `commit_snapshot` path, so live edits actually
   land in commit history end to end.
3. Full frontend navigation into `DiffView`, `ConflictResolutionView`,
   `LiveEditor`, and `PresenceIndicator` — e.g. a router with per-artifact
   and per-merge-request routes — so those already-built, already-tested
   components are reachable from the running app the same way
   `WorkspaceView` and `SearchChatPanel` now are.
4. Tree-sitter aware structural diffs extended across a codebase artifact's
   full merge flow (today it diffs a single file's function/class
   boundaries; merges still operate at the line level).
5. A conflict resolution assistant that proposes candidate merged text for
   a human to accept or edit, rather than only flagging conflicts.
6. Authentication and per-user permissions to replace the current mock user
   id scheme (`MOCK_USER_ID` / hardcoded `"user-1"`).
7. A more thorough PDF ingestion path that handles scanned pages instead of
   assuming extractable text.

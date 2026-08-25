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
  provenance (artifact id, commit ref, score), exposed over HTTP at
  `GET /api/search` (see "How to run it" below for how to call it today).
- **Frontend**: `frontend/` is currently a separate marketing landing page
  ("Aura", a premium email-client concept) built on top of this same Vite
  scaffold, at explicit request, and does not consume any Git for Research
  API. The artifact list, diff, branch/merge, live-editing, and
  presence/search UI described in earlier iterations of this project were
  built, tested, and then deleted when the frontend was repurposed — see
  "What wasn't completed" below. The only way to exercise the backend
  today is directly over HTTP (`/docs`, `scripts/e2e_smoke.py`, or
  `scripts/demo.py` for the underlying modules without HTTP).

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

**The FastAPI HTTP route layer now exists** (`backend/app/api/`), wiring
the ingestion, versioning, collaboration, and retrieval modules to real
endpoints. The easiest way to see it, without writing any client code, is
FastAPI's built-in interactive docs:

```
http://localhost:8000/docs
```

Every endpoint is listed there, grouped by tag (ingestion, versioning,
collaboration, retrieval), with its request/response schema. Click any
route, then "Try it out", fill in the fields, and "Execute" — it makes a
real HTTP call against your running backend and shows the real response.
For example: expand `POST /api/workspaces/{workspace_id}/artifacts/ingest/markdown`,
type any string as `workspace_id`, upload a `.md` file, and Execute — you
get back a real `artifact_id` you can then paste into
`GET /api/artifacts/{artifact_id}` to see it looked up from the database.
Before trying this (or any other ingestion or commit route), first call
`POST /api/users` with a `username` (and optional `display_name`) to create
a user profile, then use that exact username as the `author` value on the
ingestion/commit route you're trying — these routes now require an
`author` that resolves to a real user profile and return 404 otherwise.

**Important caveat, read before trying `docker compose up --build`**: it
was **not** run in the sandbox this project was built in (no Docker was
available there; a local Postgres 15 + pgvector install, plus a locally
run `uvicorn app.main:app`, was used for all backend testing instead). The
route layer, `scripts/e2e_smoke.py`, and the `/docs` walkthrough above were
all verified against that local setup, not against the containerized
stack — see item 4 under "What wasn't completed" below.

**To see the underlying engine work without going through HTTP at all**, run:

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
- **Frontend (historical)**: at one point this repo had a React/TypeScript
  frontend with 14 Vitest tests passing across 9 files, covering an API
  client (`fetchArtifacts`, `fetchDiff`, `fetchMergeRequest`,
  `submitResolution`, `searchQuery`) and `ArtifactList`, `WorkspaceView`,
  `DiffView`, `ConflictResolutionView`, `LiveEditor`, `PresenceIndicator`,
  and `SearchChatPanel` components, composed into `App.tsx` so the artifact
  list and search were both reachable from a single page load. **All of
  this was deleted** when `frontend/` was repurposed into the Aura landing
  page (see the Architecture section above) — it exists only in this
  repo's git history now, not in the current tree.

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
- [ ] Search and chat surface in the frontend backed by the retrieval API,
      with provenance shown on every result — `GET /api/search` exists and
      is verified working (`backend/app/api/routes_retrieval.py`), but the
      `SearchChatPanel` component that called it was deleted along with
      the rest of the pre-Aura frontend (see above); there is no frontend
      consumer of this route today, only `/docs`, `scripts/e2e_smoke.py`,
      and `scripts/demo.py`.

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

1. **No database schema creation/migration step outside the test suite.**
   The only place `Base.metadata.create_all(engine)` is called anywhere in
   this repo is inside `backend/tests/test_db_models.py`. There is no
   startup hook in `app/main.py` and no Alembic (or equivalent) migration
   that creates tables against a fresh database. A brand new
   `docker compose up` volume would need this before any endpoint that
   touches the database would work. (The locally-run backend this was
   verified against had its tables created once, by hand, via the same
   `Base.metadata.create_all(engine)` call the test suite uses — not
   through any route or startup hook.) Note that `Base.metadata.create_all(engine)`
   on its own, without a preceding `drop_all`, is additive and safe to run
   against a database that already has data (it only creates tables that
   don't yet exist) — but `backend/tests/test_db_models.py`'s own test
   deliberately calls `drop_all` first and will wipe all existing data, so
   that specific test should not be treated as the setup mechanism for a
   real database.
2. **The FastAPI route layer (`backend/app/api/`) has no automated test
   coverage.** It exists now and every endpoint has been verified by hand
   against a live server — `scripts/e2e_smoke.py` runs end to end
   (ingest → branch → conflicting commits → merge request → live conflict
   → search), and `/docs` renders and accepts real requests — but there is
   no `pytest` file using FastAPI's `TestClient` for any of
   `routes_ingestion.py`, `routes_versioning.py`, `routes_collab.py`, or
   `routes_retrieval.py`. The 76 backend tests referenced above cover the
   Python modules these routes call, not the routes' request/response
   handling, status codes, or error paths directly.
3. **`workspace_id` is a free-form, unvalidated string, not a real
   entity.** `app/db/models.py` has no `Workspace` table. `Artifact.workspace_id`
   is just a string column — any caller can pass any value to
   `POST /api/workspaces/{workspace_id}/artifacts/ingest/*` and it silently
   becomes a new implicit workspace with no existence check, no listing of
   workspaces, and no way to tell a typo from a new workspace.
4. **The crdt-relay container only runs the websocket relay, not the
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
5. **`docker compose up --build` was never actually run.** No Docker was
   available in the sandbox this was built in. `docker-compose.yml` and the
   three services' Dockerfiles are believed correct by inspection (image
   names, ports, env vars, build contexts were all cross-checked against the
   code that reads them — see the two corrections below — as far as that's
   possible without a daemon to actually build and run them), but this has
   not been verified by an actual run.
6. **There is no frontend for this backend at all today.** The
   artifact-list/diff/branch/merge/live-editing/search UI that used to
   exist in `frontend/` (see "What was completed versus not" above) was
   deleted when `frontend/` was repurposed into the Aura landing page, an
   unrelated marketing page built on request over this same Vite
   scaffold. Aura renders no data from, and makes no calls to, this
   backend. The backend's API layer is real and working (see "How to run
   it"), but the only way to exercise it today is directly over HTTP.
7. **Live-editing presence never actually broadcasts.** Nothing in the
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

1. Automated tests for the FastAPI route layer (`backend/app/api/`) using
   `TestClient`, plus a startup-time (or Alembic) schema creation step —
   together these are what would take this from "verified once by hand"
   to "the docker compose stack and `scripts/e2e_smoke.py` are covered by
   CI, not just a one-time manual run."
2. A real frontend that actually consumes this backend — an artifact list,
   diff view, branch/merge controls, and the search panel described in
   "What wasn't completed" above, calling the real `/api/...` routes (the
   pre-Aura versions of these components, deleted from this repo, are a
   reasonable starting reference in git history, but their API client
   would need rebuilding against the actual route shapes, e.g. the
   `workspace_id` path segment).
3. Wiring `crdt-relay`'s snapshot HTTP endpoint into the same running
   process as the websocket relay (or as a second container) and calling it
   from the route layer's `commit_snapshot` path, so live edits actually
   land in commit history end to end.
4. A real `Workspace` entity (instead of a free-form `workspace_id` string)
   with a listing endpoint, so a frontend has something to select from.
5. Tree-sitter aware structural diffs extended across a codebase artifact's
   full merge flow (today it diffs a single file's function/class
   boundaries; merges still operate at the line level).
6. A conflict resolution assistant that proposes candidate merged text for
   a human to accept or edit, rather than only flagging conflicts.
7. Authentication and per-user permissions to replace the current mock user
   id scheme (`MOCK_USER_ID` / hardcoded `"user-1"`).
8. A more thorough PDF ingestion path that handles scanned pages instead of
   assuming extractable text.

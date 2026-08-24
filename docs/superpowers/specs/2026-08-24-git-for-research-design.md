# Git for Research — Architecture Design

**Date:** 2026-08-24
**Context:** 13-hour hackathon, solo/pair team, fully local demo environment.
**Source brief:** `git_for_research_hackathon_problem_statement.pdf`

## Problem

Build a platform that treats research artifacts (docs, LLM chat exports, PDFs,
codebases) as first-class versioned objects, with a concurrent context layer
so multiple people can work on the same evolving body of knowledge without
overwriting each other. Four mandatory pillars: ingestion, versioning
(commit/diff/branch/merge), concurrent context (presence/CRDT/"what changed"),
retrieval (search + cross-artifact Q&A).

Evaluation weights: versioning engine correctness 35%, concurrency handling
20%, ingestion breadth 15%, retrieval quality 15%, stretch execution 10%,
demo clarity 5%. Judges will ask to see a live merge conflict and a live
semantic diff first.

## Stretch goals in scope (priority order)

1. **3-way merge for prose** with a conflict resolution UI
2. **Provenance graph** — trace a claim/paragraph back to its source
3. **Multi-agent editing** — an LLM agent opens a branch, edits, submits a
   merge request for human review

Each stretch is designed to layer on the core engine with no rework if time
runs out after an earlier one.

## Stack

- **Backend:** Python (FastAPI)
- **Frontend:** React/TypeScript
- **DB:** Postgres + pgvector (single instance — commit DAG, chunks/embeddings,
  provenance edges, merge requests, last-seen state)
- **CRDT relay:** small Node process (`y-websocket` + awareness)
- **Codebase versioning:** real git repos via `pygit2`
- **Diffing:** generic Myers sequence diff (`difflib`) over paragraphs/messages;
  `tree-sitter` for code structure; libgit2 native merge for code
- **Embeddings:** local `sentence-transformers` (no external API dependency)
- **Deployment:** single `docker-compose.yml`, fully local, no auth (mock users)

## 1. Core architectural decision: two versioning backends behind one interface

Two versioning engines are used, unified behind a single `VersionedArtifact`
interface (`commit()`, `diff(a, b)`, `branch()`, `merge()`) so ingestion,
retrieval, provenance, multi-agent PRs, and the UI never need to know which
backend an artifact uses:

- **Custom content-addressed commit DAG** (Postgres) for docs, chat exports,
  and PDFs — these aren't naturally "files in a repo," and prose/chat
  semantic diff and 3-way merge need custom token-level logic anyway, so a
  custom lightweight DAG is no more work than wrapping git for these types.
- **Real git repos** (via `pygit2`) for codebase artifacts — code already
  lives in git in the real world, so importing existing history and reusing
  libgit2's native (well-tested) line-based diff/merge is a straight win for
  this one artifact type, and it's the one the brief flags as optional/stretch
  anyway.

This was a deliberate trade against a simpler single-engine design: it costs
two code paths instead of one, but avoids forcing code files through a
prose-oriented merge model or forcing prose through a line-based one.

### Schema

Custom DAG tables:
- `blob(hash PK, content, size)` — SHA256 content-addressed, automatic dedup
- `commit(id, artifact_id, parent_ids[], blob_hash, author, message, created_at)`
  — `parent_ids` has 2 entries for merge commits
- `branch(id, artifact_id, name, head_commit_id)`
- `artifact(id, workspace_id, type, name)` — type ∈ {doc, chat, pdf}

Git backend: one bare repo per codebase artifact on disk, managed via
`pygit2`. Uploaded zips → `git init` + initial commit. Uploaded `.git` repos
→ cloned as-is, preserving existing history.

Shared cross-cutting tables (reference either a custom-DAG commit UUID or a
git OID via an opaque `commit_ref` string):
- `chunk(id, artifact_id, commit_ref, text, embedding vector, span)`
- `provenance_edge(from_chunk_id, to_chunk_id, relation)`
- `merge_request(id, artifact_id, source_branch, target_branch, status, base_commit_ref)`
- `last_seen(user_id, artifact_id, commit_ref)`

## 2. Ingestion layer

One independent parser per artifact type, each normalizing to
`(structured_content, metadata)` committed as the artifact's initial commit:

- **Markdown/plaintext** — read as-is, single blob.
- **ChatGPT export (`conversations.json`)** — schema is a tree (`mapping` of
  node id → {message, parent, children}) because ChatGPT supports
  regenerated/branching responses. Parser walks root → current leaf and
  flattens to an ordered `[{role, text, ts}]` list (alternate branches are
  discarded, not preserved — a deliberate scope cut for time). Serialized as
  JSON so message-level diffing has structure to work with.
- **Claude export** — different schema (`chat_messages` array per
  conversation, different field names, no tree structure). Separate parser,
  same normalized output shape as ChatGPT's.
- **PDF** — `pdfplumber`/`pypdf` extracts text per page →
  `[{page_num, text}]`.
- **Codebase (zip or git repo)** — existing `.git` repos are cloned directly
  into the git backend (history preserved). Zips of source files get
  `git init` + one commit of all files.

Each parser is independently testable; a malformed Claude export cannot break
ChatGPT ingestion.

## 3. Versioning engine (diff, branch, merge)

**Diff** dispatches by type but shares one primitive — Myers sequence diff
over a list of *tokens*, where "token" varies by artifact type:

- Prose (docs/PDFs): tokens = paragraphs. Paragraph-level add/remove/move,
  plus a nested word-level diff inside any *changed* paragraph — this is the
  "semantically meaningful, not byte diff" requirement.
- Chat exports: tokens = messages. Added/removed/edited messages, with the
  same nested word-level diff for an edited message's text.
- Code: tokens = top-level `tree-sitter` AST nodes (functions/classes) for
  display purposes — "function `foo` modified" rather than raw line noise.
  The git backend's native diff (line-based) is the source of truth
  underneath; tree-sitter is a presentation layer on top.

**Branch**: custom DAG → new `branch` row pointing at a chosen commit. Git
backend → `pygit2` branch creation. Both exposed identically via
`artifact.branch(name, from_commit)`.

**Merge / 3-way merge (stretch 1)**: one generic `diff3(base, ours, theirs)`
function over the same token lists used for diff (paragraphs for prose,
messages for chat). Per token: unchanged-in-both → keep base;
changed-in-one-side-only → take that side; changed-in-both differently →
**conflict**, emitted as a structured `{base, ours, theirs, position}` record
(not inline `<<<<<<<` markers) so the frontend renders a real side-by-side
conflict resolution widget — pick ours/theirs/edit-manually per conflicting
paragraph. Code merges use libgit2's native merge directly rather than the
generic diff3, since line-based code merging is already solved there.

## 4. Concurrent context layer

- **Live editing**: one Yjs document per artifact-branch, synced via a Node
  `y-websocket` relay (separate process from the Python backend — Yjs
  tooling for rich text, e.g. `y-prosemirror`, is JS-only and far more mature
  than Python CRDT equivalents). The relay holds live, uncommitted state.
- **Presence**: Yjs's built-in awareness protocol broadcasts
  `{user_id, color, cursor_position}` over the same websocket — "who's
  viewing/editing what" comes almost for free.
- **CRDT → commit DAG bridge**: a "commit" action (explicit click or periodic
  autosave) hits an HTTP endpoint on the Node relay that serializes the
  current Yjs doc to plain text and POSTs it to the Python backend, which
  creates a new Blob+Commit. This keeps the real-time layer and durable
  history cleanly decoupled — Yjs never touches Postgres directly.
- **Branching a live doc**: forking seeds a new Yjs room from a specific
  commit's content, isolated from the original room until merged back.
- **"What's changed since I last looked"**: `last_seen(user_id, artifact_id,
  commit_ref)` updated on open; on load, list commits between that ref and
  the branch head and render a "N changes since you left" banner using the
  §3 diff engine.

Scope note: codebases (git-backed) do not get live CRDT co-editing — code is
edited locally and pushed as commits, matching real-world git workflow. CRDT
applies only to docs/chats/PDFs, where live prose co-editing is the actual
ask in the brief.

## 5. Retrieval / query surface

- **Chunking**: paragraph-level (docs/PDFs), message-level (chats),
  function-level via tree-sitter (code) — the same granularity used for
  diffing, so a `chunk` row doubles as both a diff unit and a retrieval unit.
- **Embeddings**: local `sentence-transformers` (`all-MiniLM-L6-v2`) — no
  external API dependency, so retrieval works fully offline and isn't at risk
  during a local demo.
- **Store**: pgvector, same Postgres instance as everything else.
- **Query**: embed the question, cosine-similarity search across `chunk`
  (optionally filtered to a branch/commit), return top-k chunks with
  provenance metadata (artifact, commit, source type) — this alone satisfies
  "retrieve relevant context from multiple artifact types." An optional LLM
  call (Claude/GPT, if a key is available) synthesizes a natural-language
  answer citing those chunks; retrieval itself does not depend on that call
  succeeding.

## 6. Stretch goals 2 & 3

**Provenance graph**: `provenance_edge(from_chunk_id, to_chunk_id,
relation='cites')` rows. Edges are created semi-automatically: whenever a
retrieval-backed answer/paragraph is produced via the "chat with your
research history" flow, the resulting paragraph's chunk is auto-linked to
whichever source chunks were retrieved to produce it — piggybacking on
retrieval calls already being made, at near-zero extra cost. Full automatic
citation-detection NLP is out of scope. Querying provenance is a recursive
graph walk over `to_chunk_id` edges back to source artifacts/commits.

**Multi-agent editing**: an LLM agent is just another actor with a user id.
It calls the same `branch()` → edit → `commit()` API a human would, then
creates a `merge_request` row (source branch, target branch, status=open). A
human reviewer sees it in a PR-like list, opens the §3 diff view, and merges
(reusing the exact merge/3-way-merge logic) or rejects. No new engine — this
is UI + orchestration around what already exists, consistent with it being
last in priority order.

## 7. Deployment

Single `docker-compose.yml`:
- `postgres` (pgvector extension)
- `backend` — FastAPI: ingestion, diff/merge engine, git-backend adapter,
  retrieval, provenance, merge-request API
- `crdt-relay` — Node, `y-websocket` + awareness, snapshot-export endpoint
- `frontend` — React/TS: artifact browser, diff/conflict-resolution view,
  live co-editor, presence indicators, search/chat panel

No auth (mock users — explicitly out of scope per the brief). No hard
external API dependency (embeddings local; LLM synthesis best-effort).

## Explicitly out of scope (per brief)

- Full auth/user management
- Production-grade OCR
- Building a vector DB from scratch (using pgvector)
- Polished UI beyond functional clarity
- Preserving ChatGPT's alternate-branch tree structure (flattened to current
  path instead, to save ingestion complexity)
- Atomic multi-file commits for codebases beyond what git itself provides

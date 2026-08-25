# Auth & Multi-User Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace every hardcoded `'user-1'` string with a real, validated user profile — a lightweight, passwordless, local multi-profile system that every later collaboration feature (comments, issues, notifications) can anchor to.

**Architecture:** A new `users` table + `app/users.py` CRUD module on the backend, validated via a `require_user` dependency wired into every endpoint that currently accepts a client-supplied `author`/`user_id` string. On the frontend, a `ProfileContext` (mirroring the existing `ThemeContext` pattern) holds the active profile in `localStorage`, gated by a `ProfileGate` picker shown once before the rest of the app renders.

**Tech Stack:** FastAPI + SQLAlchemy + Postgres (backend, existing stack), React + TypeScript + Tailwind (frontend, existing stack). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-25-auth-multi-user-foundation-design.md`

## Global Constraints

- No passwords, no sessions/cookies/JWT — profiles are plain `{username, display_name}` records, matching the spec's explicit "lightweight local profile" scope.
- No schema changes to `merge_requests` or any table beyond the new `users` table — that's the next sub-project's job, not this one.
- Backend tests follow this repo's existing convention: real Postgres via `get_session()`/`TestClient`, no mocking (see `tests/versioning/test_dag_store.py`, `tests/test_graph_route.py`).
- Frontend has no existing test suite to extend (Vitest configured, zero test files) — frontend tasks end in a manual Playwright verification step instead of automated tests, per the spec.
- Every previously-hardcoded `'user-1'` default must be removed, not left as a fallback — callers must now supply a real profile.

---

### Task 1: `User` DB model

**Files:**
- Modify: `backend/app/db/models.py`
- Modify: `backend/tests/test_db_models.py`

**Interfaces:**
- Produces: `User` model (table `users`) with columns `id` (str pk), `username` (str, unique), `display_name` (str), `created_at` (datetime). Consumed by Task 2's `app/users.py`.

- [ ] **Step 1: Add `"users"` to the expected-tables test**

In `backend/tests/test_db_models.py`, add `"users"` to the `expected_tables` set:

```python
    expected_tables = {
        "blobs",
        "artifacts",
        "commits",
        "branches",
        "chunks",
        "provenance_edges",
        "merge_requests",
        "last_seen",
        "users",
    }
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_db_models.py -v`
Expected: FAIL — `assert expected_tables.issubset(table_names)` fails because `"users"` isn't a real table yet.

- [ ] **Step 3: Add the `User` model**

In `backend/app/db/models.py`, add (after the `LastSeen` class, at the end of the file):

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(String, unique=True)
    display_name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime)
```

No new imports needed — `uuid`, `datetime`, `String`, `DateTime`, `Mapped`, `mapped_column` are already imported at the top of this file.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_db_models.py -v`
Expected: PASS

Note: this test does `Base.metadata.drop_all(engine)` then `create_all` on the real `research` database — running it wipes all data in every table (existing repo behavior, not something this plan changes). Expect this to be a full data wipe of the dev database; that's normal for this test.

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models.py backend/tests/test_db_models.py
git commit -m "feat: add User model for lightweight multi-profile auth"
```

---

### Task 2: `app/users.py` CRUD module

**Files:**
- Create: `backend/app/users.py`
- Test: `backend/tests/test_users.py`

**Interfaces:**
- Consumes: `User` model from Task 1 (`app.db.models.User`).
- Produces: `create_user(session, username, display_name=None) -> str` (returns user id, raises `ValueError` on duplicate username), `get_user_by_username(session, username) -> User` (raises `ValueError` if not found), `list_users(session) -> list[User]`. Consumed by Task 3's `require_user` and `routes_users.py`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_users.py`:

```python
import uuid

import pytest

from app.db.base import get_session
from app.users import create_user, get_user_by_username, list_users


def test_create_user_and_get_by_username():
    username = f"researcher-{uuid.uuid4()}"

    with get_session() as session:
        user_id = create_user(session, username, display_name="Ada Researcher")

        fetched = get_user_by_username(session, username)

        assert fetched.id == user_id
        assert fetched.username == username
        assert fetched.display_name == "Ada Researcher"


def test_create_user_defaults_display_name_to_username():
    username = f"researcher-{uuid.uuid4()}"

    with get_session() as session:
        create_user(session, username)

        fetched = get_user_by_username(session, username)

        assert fetched.display_name == username


def test_create_user_rejects_duplicate_username():
    username = f"researcher-{uuid.uuid4()}"

    with get_session() as session:
        create_user(session, username)

        with pytest.raises(ValueError):
            create_user(session, username)


def test_get_user_by_username_raises_for_unknown_username():
    with get_session() as session:
        with pytest.raises(ValueError):
            get_user_by_username(session, f"nobody-{uuid.uuid4()}")


def test_list_users_includes_created_user():
    username = f"researcher-{uuid.uuid4()}"

    with get_session() as session:
        create_user(session, username)

        usernames = [u.username for u in list_users(session)]

        assert username in usernames
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_users.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.users'`

- [ ] **Step 3: Implement `app/users.py`**

Create `backend/app/users.py`:

```python
import uuid
from datetime import datetime, timezone

from app.db.models import User


def create_user(session, username: str, display_name: str = None) -> str:
    existing = session.query(User).filter_by(username=username).one_or_none()
    if existing is not None:
        raise ValueError(f"username '{username}' already exists")

    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        username=username,
        display_name=display_name or username,
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    session.commit()
    return user_id


def get_user_by_username(session, username: str) -> User:
    user = session.query(User).filter_by(username=username).one_or_none()
    if user is None:
        raise ValueError(f"user not found for username {username}")
    return user


def list_users(session) -> list:
    return session.query(User).order_by(User.created_at).all()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_users.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/users.py backend/tests/test_users.py
git commit -m "feat: add users CRUD module"
```

---

### Task 3: `require_user` helper + `routes_users.py` (profile API)

**Files:**
- Modify: `backend/app/api/deps.py`
- Create: `backend/app/api/routes_users.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_users_route.py`

**Interfaces:**
- Consumes: `create_user`, `get_user_by_username`, `list_users` from Task 2 (`app.users`).
- Produces: `require_user(db, username)` in `app/api/deps.py` (raises `fastapi.HTTPException(404)` if unknown — consumed by Task 4 and Task 5). Routes: `POST /api/users` (body `{username, display_name?}`, 409 on duplicate), `GET /api/users` (list, shape `[{id, username, display_name}]`).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_users_route.py`:

```python
import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_user_route_returns_created_user():
    username = f"researcher-{uuid.uuid4()}"

    response = client.post("/api/users", json={"username": username, "display_name": "Ada"})

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == username
    assert body["display_name"] == "Ada"
    assert "id" in body


def test_create_user_route_defaults_display_name():
    username = f"researcher-{uuid.uuid4()}"

    response = client.post("/api/users", json={"username": username})

    assert response.status_code == 200
    assert response.json()["display_name"] == username


def test_create_user_route_conflicts_on_duplicate_username():
    username = f"researcher-{uuid.uuid4()}"
    client.post("/api/users", json={"username": username})

    response = client.post("/api/users", json={"username": username})

    assert response.status_code == 409


def test_list_users_route_includes_created_user():
    username = f"researcher-{uuid.uuid4()}"
    client.post("/api/users", json={"username": username})

    response = client.get("/api/users")

    assert response.status_code == 200
    usernames = [u["username"] for u in response.json()]
    assert username in usernames
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_users_route.py -v`
Expected: FAIL with 404s (no `/api/users` route registered yet)

- [ ] **Step 3: Add `require_user` to `deps.py`**

Replace the full contents of `backend/app/api/deps.py` with:

```python
from fastapi import HTTPException

from app.db.base import get_session
from app.users import get_user_by_username
from app.versioning.diff_engine import tokenize_messages, tokenize_paragraphs


def get_db():
    with get_session() as session:
        yield session


def tokenizer_for_type(artifact_type: str):
    if artifact_type == "chat":
        return tokenize_messages
    return tokenize_paragraphs


def require_user(db, username: str):
    try:
        return get_user_by_username(db, username)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"user '{username}' not found")
```

- [ ] **Step 4: Create `routes_users.py`**

Create `backend/app/api/routes_users.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.users import create_user, list_users

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    display_name: str | None = None


@router.post("/users")
def create_user_route(body: UserCreate, db: Session = Depends(get_db)):
    try:
        user_id = create_user(db, body.username, body.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"id": user_id, "username": body.username, "display_name": body.display_name or body.username}


@router.get("/users")
def list_users_route(db: Session = Depends(get_db)):
    rows = list_users(db)
    return [{"id": u.id, "username": u.username, "display_name": u.display_name} for u in rows]
```

- [ ] **Step 5: Register the router in `main.py`**

In `backend/app/main.py`, change the import line:

```python
from app.api import routes_collab, routes_ingestion, routes_retrieval, routes_users, routes_versioning
```

And add, alongside the other `include_router` calls:

```python
app.include_router(routes_users.router, prefix="/api", tags=["users"])
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_users_route.py -v`
Expected: PASS (4 tests)

- [ ] **Step 7: Run the full backend suite to check nothing broke**

Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/deps.py backend/app/api/routes_users.py backend/app/main.py backend/tests/test_users_route.py
git commit -m "feat: add users API (create/list profiles) and require_user validation helper"
```

---

### Task 4: Validate identity on commit/seen/changes routes

**Files:**
- Modify: `backend/app/api/routes_versioning.py`
- Test: `backend/tests/test_identity_validation.py`

**Interfaces:**
- Consumes: `require_user` from Task 3 (`app.api.deps`), `create_user` from Task 2 (`app.users`) for test setup.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_identity_validation.py`:

```python
import uuid

from fastapi.testclient import TestClient

from app.artifacts import create_artifact
from app.db.base import get_session
from app.main import app
from app.users import create_user
from app.versioning.dag_store import create_blob, create_branch, create_commit

client = TestClient(app)


def _make_artifact_with_main_branch():
    with get_session() as session:
        artifact_id = create_artifact(session, str(uuid.uuid4()), "doc", "identity fixture")
        blob_hash = create_blob(session, f"root content {uuid.uuid4()}")
        root_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=blob_hash,
            parent_ids=[],
            author="seed-author",
            message="root",
        )
        create_branch(session, artifact_id=artifact_id, name="main", head_commit_id=root_id)
    return artifact_id


def test_commit_route_rejects_unknown_author():
    artifact_id = _make_artifact_with_main_branch()

    response = client.post(
        f"/api/artifacts/{artifact_id}/commits",
        json={
            "branch_name": "main",
            "content": "new content",
            "message": "edit",
            "author": f"nobody-{uuid.uuid4()}",
        },
    )

    assert response.status_code == 404


def test_commit_route_accepts_known_author():
    artifact_id = _make_artifact_with_main_branch()
    username = f"researcher-{uuid.uuid4()}"
    with get_session() as session:
        create_user(session, username)

    response = client.post(
        f"/api/artifacts/{artifact_id}/commits",
        json={"branch_name": "main", "content": "new content", "message": "edit", "author": username},
    )

    assert response.status_code == 200


def test_mark_seen_route_rejects_unknown_user():
    artifact_id = _make_artifact_with_main_branch()

    response = client.post(
        f"/api/artifacts/{artifact_id}/seen",
        json={"user_id": f"nobody-{uuid.uuid4()}", "commit_ref": "irrelevant"},
    )

    assert response.status_code == 404


def test_changes_route_rejects_unknown_user():
    artifact_id = _make_artifact_with_main_branch()

    response = client.get(
        f"/api/artifacts/{artifact_id}/changes",
        params={"user_id": f"nobody-{uuid.uuid4()}", "branch_name": "main"},
    )

    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_identity_validation.py -v`
Expected: FAIL — all four currently return 200/other statuses since no validation exists yet.

- [ ] **Step 3: Wire `require_user` into the three routes**

In `backend/app/api/routes_versioning.py`:

Change the import line:

```python
from app.api.deps import get_db, require_user, tokenizer_for_type
```

Change `CommitRequest` to drop the stale hardcoded default:

```python
class CommitRequest(BaseModel):
    branch_name: str
    content: str
    message: str
    author: str
```

In `create_commit_route`, add validation right after the artifact lookup:

```python
@router.post("/artifacts/{artifact_id}/commits")
def create_commit_route(artifact_id: str, body: CommitRequest, db: Session = Depends(get_db)):
    a = _artifact_or_404(db, artifact_id)
    require_user(db, body.author)
    artifact = DagVersionedArtifact(db, artifact_id, tokenizer_for_type(a.type))
    ...
```

(rest of the function body unchanged)

In `get_changes_route`, add validation right after the artifact lookup:

```python
@router.get("/artifacts/{artifact_id}/changes")
def get_changes_route(
    artifact_id: str, user_id: str, branch_name: str = "main", db: Session = Depends(get_db)
):
    _artifact_or_404(db, artifact_id)
    require_user(db, user_id)
    commits = get_changes_since(db, user_id, artifact_id, branch_name)
    ...
```

In `mark_seen_route`, add validation right after the artifact lookup:

```python
@router.post("/artifacts/{artifact_id}/seen")
def mark_seen_route(artifact_id: str, body: SeenRequest, db: Session = Depends(get_db)):
    _artifact_or_404(db, artifact_id)
    require_user(db, body.user_id)
    mark_seen(db, body.user_id, artifact_id, body.commit_ref)
    return {"status": "ok"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_identity_validation.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
Expected: all pass. (`scripts/e2e_smoke.py` is a separate manual script, not part of pytest — it will need a real author now; that's addressed by this plan's frontend tasks, not this one.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes_versioning.py backend/tests/test_identity_validation.py
git commit -m "feat: validate author/user_id against real users on commit/seen/changes routes"
```

---

### Task 5: Ingestion routes accept + validate a real author

**Files:**
- Modify: `backend/app/api/routes_ingestion.py`
- Test: `backend/tests/test_identity_validation.py` (extend from Task 4)

**Interfaces:**
- Consumes: `require_user` from Task 3.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_identity_validation.py`:

```python
def test_ingest_markdown_route_rejects_unknown_author():
    response = client.post(
        "/api/workspaces/demo-workspace/artifacts/ingest/markdown",
        files={"file": ("note.md", b"# Hello\n\nWorld", "text/markdown")},
        data={"author": f"nobody-{uuid.uuid4()}"},
    )

    assert response.status_code == 404


def test_ingest_markdown_route_accepts_known_author():
    username = f"researcher-{uuid.uuid4()}"
    with get_session() as session:
        create_user(session, username)

    response = client.post(
        "/api/workspaces/demo-workspace/artifacts/ingest/markdown",
        files={"file": ("note.md", b"# Hello\n\nWorld", "text/markdown")},
        data={"author": username},
    )

    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_identity_validation.py -v -k ingest`
Expected: FAIL — the route doesn't accept an `author` field yet (422, missing route param handling), and doesn't validate it.

- [ ] **Step 3: Update `routes_ingestion.py` to accept and validate `author`**

Replace the full contents of `backend/app/api/routes_ingestion.py`:

```python
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_user, tokenizer_for_type
from app.artifacts import create_artifact
from app.ingestion.chatgpt_parser import parse_chatgpt_export
from app.ingestion.claude_parser import parse_claude_export
from app.ingestion.markdown_parser import parse_markdown
from app.ingestion.pdf_parser import parse_pdf
from app.retrieval.chunker import chunk_messages, chunk_prose
from app.retrieval.query import index_chunks
from app.versioning.dag_adapter import DagVersionedArtifact

router = APIRouter()


def _commit_and_index(session: Session, artifact_id: str, artifact_type: str, content: str, author: str) -> str:
    artifact = DagVersionedArtifact(session, artifact_id, tokenizer_for_type(artifact_type))
    commit_ref = artifact.commit(content, author, "initial import", None)
    artifact.branch("main", commit_ref)

    chunks = chunk_messages(content) if artifact_type == "chat" else chunk_prose(content)
    index_chunks(session, artifact_id, commit_ref, chunks)
    return commit_ref


@router.post("/workspaces/{workspace_id}/artifacts/ingest/markdown")
async def ingest_markdown(
    workspace_id: str, file: UploadFile = File(...), author: str = Form(...), db: Session = Depends(get_db)
):
    require_user(db, author)
    raw = await file.read()
    parsed = parse_markdown(raw, file.filename or "untitled.md")
    artifact_id = create_artifact(db, workspace_id, parsed.artifact_type, parsed.name)
    commit_ref = _commit_and_index(db, artifact_id, parsed.artifact_type, parsed.content, author)
    return {"artifact_id": artifact_id, "commit_ref": commit_ref}


@router.post("/workspaces/{workspace_id}/artifacts/ingest/chatgpt")
async def ingest_chatgpt(
    workspace_id: str, file: UploadFile = File(...), author: str = Form(...), db: Session = Depends(get_db)
):
    require_user(db, author)
    raw = await file.read()
    try:
        parsed_list = parse_chatgpt_export(raw)
    except (KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid ChatGPT export: {exc}")

    results = []
    for parsed in parsed_list:
        artifact_id = create_artifact(db, workspace_id, parsed.artifact_type, parsed.name)
        commit_ref = _commit_and_index(db, artifact_id, parsed.artifact_type, parsed.content, author)
        results.append({"artifact_id": artifact_id, "commit_ref": commit_ref, "name": parsed.name})
    return {"artifacts": results}


@router.post("/workspaces/{workspace_id}/artifacts/ingest/claude")
async def ingest_claude(
    workspace_id: str, file: UploadFile = File(...), author: str = Form(...), db: Session = Depends(get_db)
):
    require_user(db, author)
    raw = await file.read()
    try:
        parsed_list = parse_claude_export(raw)
    except (KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid Claude export: {exc}")

    results = []
    for parsed in parsed_list:
        artifact_id = create_artifact(db, workspace_id, parsed.artifact_type, parsed.name)
        commit_ref = _commit_and_index(db, artifact_id, parsed.artifact_type, parsed.content, author)
        results.append({"artifact_id": artifact_id, "commit_ref": commit_ref, "name": parsed.name})
    return {"artifacts": results}


@router.post("/workspaces/{workspace_id}/artifacts/ingest/pdf")
async def ingest_pdf(
    workspace_id: str, file: UploadFile = File(...), author: str = Form(...), db: Session = Depends(get_db)
):
    require_user(db, author)
    raw = await file.read()
    parsed = parse_pdf(raw, file.filename or "untitled.pdf")

    # parse_pdf's content is a JSON array of {"page": n, "text": ...} objects,
    # which has no blank lines for tokenize_paragraphs to split on. Join the
    # page texts with a blank line so the committed content is real,
    # paragraph-diffable prose instead of an opaque JSON blob.
    pages = json.loads(parsed.content)
    joined_content = "\n\n".join(page["text"] for page in pages if page.get("text"))

    artifact_id = create_artifact(db, workspace_id, parsed.artifact_type, parsed.name)
    commit_ref = _commit_and_index(db, artifact_id, parsed.artifact_type, joined_content, author)
    return {"artifact_id": artifact_id, "commit_ref": commit_ref}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_identity_validation.py -v`
Expected: PASS (6 tests total)

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes_ingestion.py backend/tests/test_identity_validation.py
git commit -m "feat: require and validate a real author on ingestion routes"
```

---

### Task 6: Frontend API client — profile endpoints + drop hardcoded author defaults

**Files:**
- Modify: `frontend/src/api.ts`

**Interfaces:**
- Produces: `UserProfile` type, `listUsers(): Promise<UserProfile[]>`, `createUser(username, displayName?): Promise<UserProfile>`. Consumed by Task 8 (`ProfileGate`).
- Changes signatures consumed by Task 10: `ingestArtifact(workspaceId, kind, file, author)` (now requires `author`), `createCommit(..., author)` (no default), `getChanges`/`markSeen` unchanged in signature (already require `userId`).

- [ ] **Step 1: Add the `UserProfile` type and API functions**

In `frontend/src/api.ts`, add after the `ArtifactGraph` interface:

```typescript
export interface UserProfile {
  id: string
  username: string
  display_name: string
}

export function listUsers(): Promise<UserProfile[]> {
  return request('/users')
}

export function createUser(username: string, displayName?: string): Promise<UserProfile> {
  return postJson('/users', { username, display_name: displayName })
}
```

- [ ] **Step 2: Update `ingestArtifact` to require and send `author`**

Replace the `ingestArtifact` function:

```typescript
export async function ingestArtifact(
  workspaceId: string,
  kind: IngestKind,
  file: File,
  author: string,
): Promise<string[]> {
  const form = new FormData()
  form.append('file', file)
  form.append('author', author)
  const body = await request<
    { artifact_id: string; commit_ref: string } | { artifacts: { artifact_id: string }[] }
  >(`/workspaces/${encodeURIComponent(workspaceId)}/artifacts/ingest/${kind}`, {
    method: 'POST',
    body: form,
  })
  if ('artifact_id' in body) return [body.artifact_id]
  return body.artifacts.map((a) => a.artifact_id)
}
```

- [ ] **Step 3: Drop `createCommit`'s hardcoded default**

Change:

```typescript
export function createCommit(
  artifactId: string,
  branchName: string,
  content: string,
  message: string,
  author: string,
): Promise<{ commit_ref: string; branch_name: string }> {
  return postJson(`/artifacts/${artifactId}/commits`, { branch_name: branchName, content, message, author })
}
```

(only the `author = 'user-1'` → `author: string` default removal changes)

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: FAILS at this point — `IngestPanel.tsx` and `BranchesPanel.tsx` call these functions with the old signatures. That's expected; Task 10 fixes the call sites. Confirm the errors are exactly the two call-site mismatches (in `IngestPanel.tsx` and `BranchesPanel.tsx`) and nothing else, then continue — don't fix call sites here, that's Task 10's job.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api.ts
git commit -m "feat: add profile API client functions, require real author on commit/ingest calls"
```

---

### Task 7: `ProfileContext`

**Files:**
- Create: `frontend/src/profile/ProfileContext.tsx`

**Interfaces:**
- Produces: `Profile` type (`{username, displayName}`), `ProfileProvider` component, `useProfile()` hook returning `{profile: Profile | null, setProfile, clearProfile}`. Consumed by Task 8, 9, 10.

- [ ] **Step 1: Create the context**

Create `frontend/src/profile/ProfileContext.tsx`:

```tsx
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export interface Profile {
  username: string
  displayName: string
}

const STORAGE_KEY = 'gfr-profile'

const ProfileContext = createContext<{
  profile: Profile | null
  setProfile: (profile: Profile) => void
  clearProfile: () => void
} | null>(null)

function readInitialProfile(): Profile | null {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (!stored) return null
  try {
    return JSON.parse(stored) as Profile
  } catch {
    return null
  }
}

export function ProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfileState] = useState<Profile | null>(readInitialProfile)

  useEffect(() => {
    if (profile) localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
    else localStorage.removeItem(STORAGE_KEY)
  }, [profile])

  return (
    <ProfileContext.Provider
      value={{ profile, setProfile: setProfileState, clearProfile: () => setProfileState(null) }}
    >
      {children}
    </ProfileContext.Provider>
  )
}

export function useProfile() {
  const ctx = useContext(ProfileContext)
  if (!ctx) throw new Error('useProfile must be used within a ProfileProvider')
  return ctx
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: same two pre-existing call-site errors from Task 6 (`IngestPanel.tsx`, `BranchesPanel.tsx`), no new errors from this file.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/profile/ProfileContext.tsx
git commit -m "feat: add ProfileContext for local multi-profile state"
```

---

### Task 8: `ProfileGate` component

**Files:**
- Create: `frontend/src/components/ProfileGate.tsx`

**Interfaces:**
- Consumes: `useProfile` from Task 7, `listUsers`/`createUser`/`UserProfile` from Task 6.
- Produces: `ProfileGate` component (wraps children, only renders them once a profile is active). Consumed by Task 9 (wired into `App.tsx`).

- [ ] **Step 1: Create the component**

Create `frontend/src/components/ProfileGate.tsx`:

```tsx
import { useEffect, useState, type ReactNode } from 'react'
import { createUser, listUsers, type UserProfile } from '../api'
import { useProfile } from '../profile/ProfileContext'

const INPUT =
  'flex-1 rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'

export default function ProfileGate({ children }: { children: ReactNode }) {
  const { profile, setProfile } = useProfile()
  const [users, setUsers] = useState<UserProfile[]>([])
  const [newUsername, setNewUsername] = useState('')
  const [status, setStatus] = useState('')

  useEffect(() => {
    if (!profile) {
      listUsers()
        .then(setUsers)
        .catch((err) => setStatus((err as Error).message))
    }
  }, [profile])

  if (profile) return <>{children}</>

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      const user = await createUser(newUsername)
      setProfile({ username: user.username, displayName: user.display_name })
    } catch (err) {
      setStatus((err as Error).message)
    }
  }

  return (
    <div className="relative z-20 flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm rounded-xl border border-stone-200/70 bg-white/90 p-6 shadow-lg backdrop-blur-md dark:border-slate-800/70 dark:bg-slate-900/80">
        <h2 className="mb-1 text-lg font-semibold text-stone-900 dark:text-slate-100">Who's working today?</h2>
        <p className="mb-4 text-sm text-stone-600 dark:text-slate-400">
          Pick an existing profile or create a new one — no password needed.
        </p>
        {users.length > 0 && (
          <ul className="mb-4 space-y-1">
            {users.map((u) => (
              <li key={u.id}>
                <button
                  onClick={() => setProfile({ username: u.username, displayName: u.display_name })}
                  className="w-full rounded-md border border-stone-200 px-3 py-2 text-left text-sm hover:bg-stone-100 dark:border-slate-700 dark:hover:bg-slate-800"
                >
                  {u.display_name}
                </button>
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={handleCreate} className="flex gap-2">
          <input
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
            placeholder="new username"
            required
            className={INPUT}
          />
          <button
            type="submit"
            className="rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-cyan-500 dark:text-slate-950"
          >
            Create
          </button>
        </form>
        {status && <p className="mt-2 text-sm text-rose-600 dark:text-rose-400">{status}</p>}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: same two pre-existing call-site errors from Task 6, no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ProfileGate.tsx
git commit -m "feat: add ProfileGate profile picker/creation screen"
```

---

### Task 9: `ProfileSwitcher` + wire gate/provider into the app shell

**Files:**
- Create: `frontend/src/components/ui/ProfileSwitcher.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `useProfile` from Task 7, `ProfileGate` from Task 8.

- [ ] **Step 1: Create `ProfileSwitcher`**

Create `frontend/src/components/ui/ProfileSwitcher.tsx`:

```tsx
import { useProfile } from '../../profile/ProfileContext'

export default function ProfileSwitcher() {
  const { profile, clearProfile } = useProfile()
  if (!profile) return null

  return (
    <button
      onClick={clearProfile}
      title="Switch profile"
      className="rounded-full border border-stone-300 px-3 py-1.5 text-xs font-medium text-stone-600 transition-colors hover:bg-stone-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
    >
      {profile.displayName}
    </button>
  )
}
```

- [ ] **Step 2: Wrap `App` with `ProfileProvider` in `main.tsx`**

Replace `frontend/src/main.tsx` contents:

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { ThemeProvider } from './theme/ThemeContext'
import { ProfileProvider } from './profile/ProfileContext'
import './index.css'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ThemeProvider>
      <ProfileProvider>
        <App />
      </ProfileProvider>
    </ThemeProvider>
  </React.StrictMode>,
)
```

- [ ] **Step 3: Wire `ProfileGate` and `ProfileSwitcher` into `App.tsx`**

Replace `frontend/src/App.tsx` contents:

```tsx
import { useState } from 'react'
import WaveBackground from './components/WaveBackground'
import LandingPage from './components/LandingPage'
import WorkspaceApp from './components/WorkspaceApp'
import ProfileGate from './components/ProfileGate'
import ThemeToggle from './components/ui/ThemeToggle'
import ProfileSwitcher from './components/ui/ProfileSwitcher'

function App() {
  const [entered, setEntered] = useState(false)

  return (
    <div className="relative min-h-screen p-4 md:p-8">
      <WaveBackground />
      <div className="fixed right-4 top-4 z-10 flex items-center gap-2 md:right-8 md:top-8">
        <ProfileSwitcher />
        <ThemeToggle />
      </div>
      <ProfileGate>
        {entered ? (
          <WorkspaceApp onBack={() => setEntered(false)} />
        ) : (
          <LandingPage onStart={() => setEntered(true)} />
        )}
      </ProfileGate>
    </div>
  )
}

export default App
```

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: same two pre-existing call-site errors from Task 6 (`IngestPanel.tsx`, `BranchesPanel.tsx`), nothing new.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/ProfileSwitcher.tsx frontend/src/main.tsx frontend/src/App.tsx
git commit -m "feat: wire profile gate and switcher into the app shell"
```

---

### Task 10: Wire existing panels to the real profile (final integration)

**Files:**
- Modify: `frontend/src/components/IngestPanel.tsx`
- Modify: `frontend/src/components/BranchesPanel.tsx`
- Modify: `frontend/src/components/ChangesPanel.tsx`

**Interfaces:**
- Consumes: `useProfile` from Task 7, updated `ingestArtifact`/`createCommit` signatures from Task 6.

- [ ] **Step 1: Update `IngestPanel.tsx` to send the real author**

In `frontend/src/components/IngestPanel.tsx`, add the import:

```tsx
import { useProfile } from '../profile/ProfileContext'
```

Inside the component, add at the top:

```tsx
const { profile } = useProfile()
```

Change the `handleSubmit` call:

```tsx
const artifactIds = await ingestArtifact(workspaceId, kind, file, profile?.username ?? '')
```

- [ ] **Step 2: Update `BranchesPanel.tsx` to send the real author on commit**

In `frontend/src/components/BranchesPanel.tsx`, add the import:

```tsx
import { useProfile } from '../profile/ProfileContext'
```

Inside the component, add at the top:

```tsx
const { profile } = useProfile()
```

Change the `handleCommit` call:

```tsx
const result = await createCommit(artifactId, commitBranch, commitContent, commitMessage, profile?.username ?? '')
```

- [ ] **Step 3: Update `ChangesPanel.tsx` to use the real profile instead of the hardcoded constant**

In `frontend/src/components/ChangesPanel.tsx`, remove the line `const USER_ID = 'user-1'` and add the import:

```tsx
import { useProfile } from '../profile/ProfileContext'
```

Inside the component, add at the top:

```tsx
const { profile } = useProfile()
const userId = profile?.username ?? ''
```

Replace every remaining use of `USER_ID` in this file with `userId` (the `getChanges(artifactId, USER_ID, branchName)` call, the `markSeen(artifactId, USER_ID, ...)` call, and the `Card title` template string).

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS, no errors.

- [ ] **Step 5: Production build**

Run: `cd frontend && npm run build`
Expected: builds successfully.

- [ ] **Step 6: Manual end-to-end verification**

With the backend running (`cd backend && MOCK_USER_ID=user-1 .venv/bin/uvicorn app.main:app --port 8000`) and frontend running (`cd frontend && npm run dev -- --port 5173`):

1. Open the app in a browser. Confirm the `ProfileGate` picker appears (no profile stored yet).
2. Create a profile (e.g. username `alice`). Confirm the gate disappears and the profile pill (showing "alice") appears next to the theme toggle.
3. Click "Let's start using this" to enter the workspace app.
4. Ingest a small markdown file. Confirm it succeeds (was previously silently attributed to `'user-1'`; now attributed to `alice` — check via `curl http://localhost:8000/api/artifacts/<id>/graph` that `commits[0].author == "alice"`).
5. Create a branch and commit onto it via the Branches panel. Confirm the commit's author is `alice` (same graph-endpoint check).
6. Click the profile pill to switch profiles; confirm it clears back to the `ProfileGate` picker, and creating/selecting a second profile (e.g. `bob`) works and is listed alongside `alice`.
7. Check the browser console for errors — expect none.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/IngestPanel.tsx frontend/src/components/BranchesPanel.tsx frontend/src/components/ChangesPanel.tsx
git commit -m "feat: wire ingest, commit, and changes panels to the active profile"
```

---

## Post-plan note (not a task — informational)

`scripts/e2e_smoke.py` hardcodes `USER_ID = "user-1"` and posts commits without an `author` field in its ingestion calls (it predates this plan). After this plan lands, that script will fail against the now-validating backend until it's updated to create a real user first and pass it through. That update is out of scope for this plan (it's a manual verification script, not part of the pytest suite or the app itself) — flag it to the user as a known follow-up, don't silently fix it as part of this plan.

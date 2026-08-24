# Git for Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a platform that treats research artifacts (markdown/plaintext docs, ChatGPT/Claude chat exports, PDFs, and codebases) as first-class versioned objects, with a git-like commit/diff/branch/merge engine, a CRDT-backed concurrent editing layer, and a local retrieval/query surface — the four mandatory pillars of the "Git for Research" hackathon brief, plus three stretch goals (3-way merge with conflict resolution, a provenance graph, and multi-agent editing via merge requests).

**Architecture:** Two versioning backends share one `VersionedArtifact` interface (`commit`, `diff`, `branch`, `merge`, `get_content`, `branch_head`): a custom content-addressed commit DAG in Postgres for docs/chats/PDFs, and real git repos (via `pygit2`) for codebase artifacts. A Node.js CRDT relay (Yjs) handles live co-editing and periodically snapshots into the DAG as commits. Retrieval runs on local sentence-transformer embeddings in pgvector. Merge requests (PR-like objects) unify human 3-way-merge review and multi-agent editing under the same review flow.

**Tech Stack:** Python 3.11 + FastAPI backend, SQLAlchemy + Postgres + pgvector, `pygit2` for codebase version control, `tree-sitter` for code structure, `sentence-transformers` for local embeddings, a Node.js CRDT relay (`ws`, `yjs`, `y-websocket`), React + TypeScript (Vite) frontend with Vitest + React Testing Library, Docker Compose for local deployment.

**Spec:** `docs/superpowers/specs/2026-08-24-git-for-research-design.md`

## Global Constraints

- No auth/user management — mock user ids as plain strings (e.g. `user-1`).
- No external LLM/API hard dependency — embeddings are local via `sentence-transformers`; any LLM call (multi-agent editing, answer synthesis) takes an injected callable so tests run fully offline.
- Do not build a vector store from scratch — pgvector via SQLAlchemy.
- No production-grade OCR.
- UI is functional, not polished — judges score the engine.
- `get_branch_head(session, artifact_id, name)` returns `None` when the branch does not exist (never raises) — this is relied on throughout the versioning adapters for branch-name-or-commit-id ref resolution.
- `diff3_merge(...)` returns `{"merged_tokens": list[str], "conflicts": list[dict]}` — this exact key name (`merged_tokens`, not `merged`) is used by every caller.

---


### Task 1: Project scaffolding and docker-compose skeleton

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/Dockerfile`
- Create: `crdt-relay/package.json`
- Create: `crdt-relay/server.js`
- Create: `crdt-relay/Dockerfile`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/setupTests.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/Dockerfile`
- Create: `docker-compose.yml`
- Test: `backend/tests/test_health.py`
- Test: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: None. This is the first task in the plan; there is no earlier code to build on.
- Produces: a FastAPI application instance `app` in `backend/app/main.py` exposing `GET /health` returning `{"status": "ok"}`, which later backend tasks extend by calling `app.include_router(...)` on this same `app` object. A Node http server entry point at `crdt-relay/server.js` reading `process.env.PORT` (default `1234`), which later CRDT-relay tasks extend to wire in `ws`, `yjs`, `y-websocket`, and `y-protocols`. A React component `App` default-exported from `frontend/src/App.tsx`, which later frontend tasks extend with routes and additional components. A root `docker-compose.yml` defining services named exactly `postgres`, `backend`, `crdt-relay`, and `frontend` on ports `5432`, `8000`, `1234`, and `5173` respectively, which later tasks (including Task 2) reference and extend.

- [ ] **Step 1: Set up the backend project skeleton and dependencies**

Create `backend/requirements.txt`:

```text
fastapi==0.109.2
uvicorn[standard]==0.27.1
sqlalchemy==2.0.27
psycopg2-binary==2.9.9
pgvector==0.2.5
pydantic==2.6.1
pytest==8.0.1
httpx==0.26.0
```

Create `backend/app/__init__.py` as an empty file.

- [ ] **Step 2: Write the failing health check test**

Create `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: Run the test to confirm it fails**

Run: `cd backend && pip install -r requirements.txt && python -m pytest tests/test_health.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'app.main'`, because `backend/app/main.py` does not exist yet.

- [ ] **Step 4: Write the minimal health endpoint implementation**

Create `backend/app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 5: Run the test to confirm it passes**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: PASS, `1 passed`.

- [ ] **Step 6: Commit the backend scaffold**

```bash
git add backend/requirements.txt backend/app/__init__.py backend/app/main.py backend/tests/test_health.py
git commit -m "feat: scaffold FastAPI backend with health endpoint"
```

- [ ] **Step 7: Write the crdt-relay package manifest**

Create `crdt-relay/package.json`:

```json
{
  "name": "crdt-relay",
  "version": "1.0.0",
  "private": true,
  "description": "CRDT sync relay for Git for Research",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "test": "node --check server.js"
  },
  "dependencies": {
    "ws": "^8.16.0",
    "yjs": "^13.6.14",
    "y-websocket": "^1.5.1",
    "y-protocols": "^1.0.6"
  }
}
```

- [ ] **Step 8: Write the minimal crdt-relay server**

Create `crdt-relay/server.js`:

```javascript
const http = require('http')

const PORT = process.env.PORT || 1234

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify({ status: 'ok' }))
})

server.listen(PORT, () => {
  console.log(`crdt-relay listening on port ${PORT}`)
})

module.exports = server
```

- [ ] **Step 9: Confirm the server file is syntactically valid**

Run: `node --check crdt-relay/server.js`
Expected: the command exits with status `0` and prints nothing.

- [ ] **Step 10: Commit the crdt-relay scaffold**

```bash
git add crdt-relay/package.json crdt-relay/server.js
git commit -m "feat: scaffold crdt-relay node server"
```

- [ ] **Step 11: Set up the frontend project skeleton**

Create `frontend/package.json`:

```json
{
  "name": "frontend",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.2",
    "@testing-library/react": "^14.2.1",
    "@types/react": "^18.2.55",
    "@types/react-dom": "^18.2.19",
    "@vitejs/plugin-react": "^4.2.1",
    "jsdom": "^24.0.0",
    "typescript": "^5.3.3",
    "vite": "^5.1.0",
    "vitest": "^1.2.2"
  }
}
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "types": ["vitest/globals"]
  },
  "include": ["src"]
}
```

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>Git for Research</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `frontend/vite.config.ts`:

```typescript
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.ts',
  },
})
```

Create `frontend/src/setupTests.ts`:

```typescript
import '@testing-library/jest-dom'
```

Create `frontend/src/main.tsx`:

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

Create a stub `frontend/src/App.tsx` (deliberately does not render the heading yet, so the test below fails first):

```tsx
function App() {
  return <div />
}

export default App
```

- [ ] **Step 12: Write the failing frontend test**

Create `frontend/src/App.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders the heading text', () => {
    render(<App />)
    expect(screen.getByText('Git for Research')).toBeInTheDocument()
  })
})
```

- [ ] **Step 13: Run the test to confirm it fails**

Run: `cd frontend && npm install && npm test`
Expected: FAIL in `src/App.test.tsx` with an error containing `Unable to find an element with the text: Git for Research`.

- [ ] **Step 14: Write the minimal App implementation**

Replace the contents of `frontend/src/App.tsx`:

```tsx
function App() {
  return (
    <div>
      <h1>Git for Research</h1>
    </div>
  )
}

export default App
```

- [ ] **Step 15: Run the test to confirm it passes**

Run: `cd frontend && npm test`
Expected: PASS, `1 passed`.

- [ ] **Step 16: Commit the frontend scaffold**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/index.html frontend/vite.config.ts frontend/src/setupTests.ts frontend/src/main.tsx frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: scaffold Vite React frontend with heading test"
```

- [ ] **Step 17: Write the Dockerfiles and root docker-compose.yml**

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `crdt-relay/Dockerfile`:

```dockerfile
FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev

COPY server.js ./

EXPOSE 1234

CMD ["node", "server.js"]
```

Create `frontend/Dockerfile`:

```dockerfile
FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
```

Create `docker-compose.yml` at the repo root:

```yaml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: research
      POSTGRES_USER: research
      POSTGRES_PASSWORD: research
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://research:research@postgres:5432/research
    depends_on:
      - postgres

  crdt-relay:
    build: ./crdt-relay
    ports:
      - "1234:1234"

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
```

- [ ] **Step 18: Validate the compose file**

Run: `docker compose config`
Expected: the command exits with status `0` and prints the fully resolved compose configuration with no errors.

- [ ] **Step 19: Commit the Dockerfiles and docker-compose.yml**

```bash
git add backend/Dockerfile crdt-relay/Dockerfile frontend/Dockerfile docker-compose.yml
git commit -m "feat: add per-service Dockerfiles and root docker-compose skeleton"
```

### Task 2: Database schema

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/models.py`
- Create: `backend/app/db/init.sql`
- Modify: `docker-compose.yml:4-11`
- Test: `backend/tests/test_db_models.py`

**Interfaces:**
- Consumes: `backend/requirements.txt` from Task 1 already installs `sqlalchemy`, `psycopg2-binary`, `pgvector`, and `pydantic`. `docker-compose.yml` from Task 1 already defines the `postgres` service (image `pgvector/pgvector:pg16`, env `POSTGRES_DB=research`, `POSTGRES_USER=research`, `POSTGRES_PASSWORD=research`, port `5432`) on lines 4-11, which this task extends with an init-script volume mount.
- Produces: `get_session()`, a context manager in `backend/app/db/base.py` yielding a SQLAlchemy `Session`, importable as `from app.db.base import get_session`. `Blob`, `Artifact`, `Commit`, `Branch`, `Chunk`, `ProvenanceEdge`, `MergeRequest`, `LastSeen` ORM classes in `backend/app/db/models.py`, importable as `from app.db.models import Blob, Artifact, Commit, Branch, Chunk, ProvenanceEdge, MergeRequest, LastSeen`, for later tasks (versioning engine, embeddings pipeline, merge logic, presence tracking) to build on.

- [ ] **Step 1: Write the failing table-creation test**

Create `backend/tests/test_db_models.py`:

```python
import os

from sqlalchemy import create_engine, inspect

from app.db.base import Base
import app.db.models  # noqa: F401  registers all model tables on Base.metadata

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://research:research@localhost:5432/research"
)


def test_all_tables_are_created():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    expected_tables = {
        "blobs",
        "artifacts",
        "commits",
        "branches",
        "chunks",
        "provenance_edges",
        "merge_requests",
        "last_seen",
    }

    assert expected_tables.issubset(table_names)

    engine.dispose()
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `cd backend && python -m pytest tests/test_db_models.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'app.db'`, because `backend/app/db/` does not exist yet.

- [ ] **Step 3: Create the engine, session, and declarative base**

Create `backend/app/db/__init__.py` as an empty file.

Create `backend/app/db/base.py`:

```python
import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://research:research@localhost:5432/research"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 4: Create the ORM models**

Create `backend/app/db/models.py`:

```python
import uuid
from datetime import datetime
from typing import List

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Blob(Base):
    __tablename__ = "blobs"

    hash: Mapped[str] = mapped_column(String, primary_key=True)
    content: Mapped[str] = mapped_column(String)
    size: Mapped[int] = mapped_column(Integer)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)


class Commit(Base):
    __tablename__ = "commits"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String)
    parent_ids: Mapped[List[str]] = mapped_column(JSON)
    blob_hash: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    head_commit_id: Mapped[str] = mapped_column(String)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String)
    commit_ref: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(String)
    embedding: Mapped[List[float]] = mapped_column(Vector(384))
    span: Mapped[str] = mapped_column(String)


class ProvenanceEdge(Base):
    __tablename__ = "provenance_edges"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    from_chunk_id: Mapped[str] = mapped_column(String)
    to_chunk_id: Mapped[str] = mapped_column(String)
    relation: Mapped[str] = mapped_column(String)


class MergeRequest(Base):
    __tablename__ = "merge_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String)
    source_branch: Mapped[str] = mapped_column(String)
    target_branch: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    base_commit_ref: Mapped[str] = mapped_column(String)


class LastSeen(Base):
    __tablename__ = "last_seen"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String, primary_key=True)
    commit_ref: Mapped[str] = mapped_column(String)
```

- [ ] **Step 5: Create the init script and mount it in docker-compose**

Create `backend/app/db/init.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Modify `docker-compose.yml`, replacing lines 4-11 (the `postgres` service block) with:

```yaml
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: research
      POSTGRES_USER: research
      POSTGRES_PASSWORD: research
    ports:
      - "5432:5432"
    volumes:
      - ./backend/app/db/init.sql:/docker-entrypoint-initdb.d/init.sql
```

- [ ] **Step 6: Start a fresh Postgres container**

Run:

```bash
docker compose down -v
docker compose up -d postgres
docker compose exec postgres pg_isready -U research
```

Expected: the last command prints `/var/run/postgresql:5432 - accepting connections`, confirming the container initialized with `init.sql` and the `vector` extension is available.

- [ ] **Step 7: Run the test to confirm it passes**

Run: `cd backend && python -m pytest tests/test_db_models.py -v`
Expected: PASS, `1 passed`.

- [ ] **Step 8: Commit the database schema**

```bash
git add backend/app/db/__init__.py backend/app/db/base.py backend/app/db/models.py backend/app/db/init.sql backend/tests/test_db_models.py docker-compose.yml
git commit -m "feat: add SQLAlchemy database schema with pgvector-backed chunk embeddings"
```

### Task 3: Custom DAG Core — Blob and Commit Storage

**Files:**
- Create: backend/app/versioning/dag_store.py
- Test: backend/tests/versioning/test_dag_store.py

**Interfaces:**
- Consumes: `get_session()` from `app.db.base` (context manager yielding a session); `Blob(hash, content, size)`, `Commit(id, artifact_id, parent_ids, blob_hash, author, message, created_at)` from `app.db.models`.
- Produces: `create_blob(session, content: str) -> str`, `get_blob_content(session, blob_hash: str) -> str`, `create_commit(session, artifact_id: str, blob_hash: str, parent_ids: list, author: str, message: str) -> str`, `get_commit(session, commit_id: str) -> Commit`, all in `backend/app/versioning/dag_store.py`.

- [ ] **Step 1: Write a failing test for content-addressed blob creation**

Create `backend/tests/versioning/test_dag_store.py` with a test that creates the same content twice and different content once, asserting the hash is stable, dedup happens, and different content produces a different hash.

```python
import uuid

from app.db.base import get_session
from app.db.models import Blob
from app.versioning.dag_store import create_blob, get_blob_content


def test_create_blob_dedups_and_different_content_gets_different_hash():
    content_a = f"paragraph one {uuid.uuid4()}"
    content_b = f"paragraph two {uuid.uuid4()}"

    with get_session() as session:
        hash_a1 = create_blob(session, content_a)
        hash_a2 = create_blob(session, content_a)
        hash_b = create_blob(session, content_b)

        assert hash_a1 == hash_a2
        assert hash_a1 != hash_b

        rows = session.query(Blob).filter(Blob.hash == hash_a1).all()
        assert len(rows) == 1

        assert get_blob_content(session, hash_a1) == content_a
```

- [ ] **Step 2: Run the test and confirm it fails**

Command: `cd backend && pytest tests/versioning/test_dag_store.py -v`

Expected failure, because `app/versioning/dag_store.py` does not exist yet:

```
ModuleNotFoundError: No module named 'app.versioning.dag_store'
```

- [ ] **Step 3: Implement create_blob and get_blob_content**

Create `backend/app/versioning/dag_store.py`:

```python
import hashlib

from app.db.models import Blob


def create_blob(session, content: str) -> str:
    blob_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    existing = session.get(Blob, blob_hash)
    if existing is None:
        blob = Blob(hash=blob_hash, content=content, size=len(content.encode("utf-8")))
        session.add(blob)
        session.commit()
    return blob_hash


def get_blob_content(session, blob_hash: str) -> str:
    blob = session.get(Blob, blob_hash)
    if blob is None:
        raise ValueError(f"blob not found for hash {blob_hash}")
    return blob.content
```

- [ ] **Step 4: Run the test and confirm it passes**

Command: `cd backend && pytest tests/versioning/test_dag_store.py -v`

Expected output: `1 passed`

- [ ] **Step 5: Commit the blob layer**

```bash
git add backend/app/versioning/dag_store.py backend/tests/versioning/test_dag_store.py
git commit -m "Add content-addressed blob storage with sha256 dedup"
```

- [ ] **Step 6: Write a failing test for commit creation and retrieval**

Extend `backend/tests/versioning/test_dag_store.py` to import `create_commit` and `get_commit` and add a test that chains two commits and checks the stored parent_ids:

```python
import uuid

from app.db.base import get_session
from app.db.models import Blob
from app.versioning.dag_store import (
    create_blob,
    get_blob_content,
    create_commit,
    get_commit,
)


def test_create_blob_dedups_and_different_content_gets_different_hash():
    content_a = f"paragraph one {uuid.uuid4()}"
    content_b = f"paragraph two {uuid.uuid4()}"

    with get_session() as session:
        hash_a1 = create_blob(session, content_a)
        hash_a2 = create_blob(session, content_a)
        hash_b = create_blob(session, content_b)

        assert hash_a1 == hash_a2
        assert hash_a1 != hash_b

        rows = session.query(Blob).filter(Blob.hash == hash_a1).all()
        assert len(rows) == 1

        assert get_blob_content(session, hash_a1) == content_a


def test_create_commit_stores_parent_ids_and_get_commit_retrieves_it():
    artifact_id = str(uuid.uuid4())

    with get_session() as session:
        parent_blob_hash = create_blob(session, f"root content {uuid.uuid4()}")
        parent_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=parent_blob_hash,
            parent_ids=[],
            author="user-1",
            message="initial commit",
        )

        child_blob_hash = create_blob(session, f"child content {uuid.uuid4()}")
        child_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=child_blob_hash,
            parent_ids=[parent_commit_id],
            author="user-1",
            message="second commit",
        )

        fetched = get_commit(session, child_commit_id)

        assert fetched.id == child_commit_id
        assert fetched.artifact_id == artifact_id
        assert fetched.parent_ids == [parent_commit_id]
        assert fetched.blob_hash == child_blob_hash
        assert fetched.author == "user-1"
        assert fetched.message == "second commit"
```

- [ ] **Step 7: Run the test and confirm it fails**

Command: `cd backend && pytest tests/versioning/test_dag_store.py -v`

Expected failure, because `create_commit` and `get_commit` are not defined yet:

```
ImportError: cannot import name 'create_commit' from 'app.versioning.dag_store'
```

- [ ] **Step 8: Implement create_commit and get_commit**

Update `backend/app/versioning/dag_store.py`:

```python
import hashlib
import uuid

from app.db.models import Blob, Commit


def create_blob(session, content: str) -> str:
    blob_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    existing = session.get(Blob, blob_hash)
    if existing is None:
        blob = Blob(hash=blob_hash, content=content, size=len(content.encode("utf-8")))
        session.add(blob)
        session.commit()
    return blob_hash


def get_blob_content(session, blob_hash: str) -> str:
    blob = session.get(Blob, blob_hash)
    if blob is None:
        raise ValueError(f"blob not found for hash {blob_hash}")
    return blob.content


def create_commit(
    session,
    artifact_id: str,
    blob_hash: str,
    parent_ids: list,
    author: str,
    message: str,
) -> str:
    commit_id = str(uuid.uuid4())
    commit = Commit(
        id=commit_id,
        artifact_id=artifact_id,
        parent_ids=parent_ids,
        blob_hash=blob_hash,
        author=author,
        message=message,
    )
    session.add(commit)
    session.commit()
    return commit_id


def get_commit(session, commit_id: str) -> Commit:
    commit = session.get(Commit, commit_id)
    if commit is None:
        raise ValueError(f"commit not found for id {commit_id}")
    return commit
```

- [ ] **Step 9: Run the test and confirm it passes**

Command: `cd backend && pytest tests/versioning/test_dag_store.py -v`

Expected output: `2 passed`

- [ ] **Step 10: Commit the commit layer**

```bash
git add backend/app/versioning/dag_store.py backend/tests/versioning/test_dag_store.py
git commit -m "Add commit creation and retrieval to the DAG store"
```

### Task 4: Custom DAG Core — Branch Pointers

**Files:**
- Modify: backend/app/versioning/dag_store.py
- Modify (test): backend/tests/versioning/test_dag_store.py

**Interfaces:**
- Consumes: `get_session()` from `app.db.base`; `Branch(id, artifact_id, name, head_commit_id)` from `app.db.models`; `create_blob(session, content)` and `create_commit(session, artifact_id, blob_hash, parent_ids, author, message)` from `app.versioning.dag_store`, produced in Task 3.
- Produces: `create_branch(session, artifact_id: str, name: str, head_commit_id: str) -> None`, `get_branch_head(session, artifact_id: str, name: str) -> Optional[str]` (returns `None` if the branch does not exist), `update_branch_head(session, artifact_id: str, name: str, new_commit_id: str) -> None` (raises `ValueError` if the branch does not exist — unlike `get_branch_head`, this operation has no valid "doesn't exist" outcome), all in `backend/app/versioning/dag_store.py`.

- [ ] **Step 1: Write a failing test for branch creation and head lookup**

Extend `backend/tests/versioning/test_dag_store.py` to import `create_branch` and `get_branch_head`, and add tests for a successful lookup and for a missing branch returning `None` (this adapter-facing contract — `None`, not an exception, on a missing branch — is relied on throughout later tasks, e.g. `DagVersionedArtifact._resolve_commit_id`'s branch-name-or-commit-id fallback):

```python
import uuid

from app.db.base import get_session
from app.db.models import Blob
from app.versioning.dag_store import (
    create_blob,
    get_blob_content,
    create_commit,
    get_commit,
    create_branch,
    get_branch_head,
)


def test_create_blob_dedups_and_different_content_gets_different_hash():
    content_a = f"paragraph one {uuid.uuid4()}"
    content_b = f"paragraph two {uuid.uuid4()}"

    with get_session() as session:
        hash_a1 = create_blob(session, content_a)
        hash_a2 = create_blob(session, content_a)
        hash_b = create_blob(session, content_b)

        assert hash_a1 == hash_a2
        assert hash_a1 != hash_b

        rows = session.query(Blob).filter(Blob.hash == hash_a1).all()
        assert len(rows) == 1

        assert get_blob_content(session, hash_a1) == content_a


def test_create_commit_stores_parent_ids_and_get_commit_retrieves_it():
    artifact_id = str(uuid.uuid4())

    with get_session() as session:
        parent_blob_hash = create_blob(session, f"root content {uuid.uuid4()}")
        parent_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=parent_blob_hash,
            parent_ids=[],
            author="user-1",
            message="initial commit",
        )

        child_blob_hash = create_blob(session, f"child content {uuid.uuid4()}")
        child_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=child_blob_hash,
            parent_ids=[parent_commit_id],
            author="user-1",
            message="second commit",
        )

        fetched = get_commit(session, child_commit_id)

        assert fetched.id == child_commit_id
        assert fetched.artifact_id == artifact_id
        assert fetched.parent_ids == [parent_commit_id]
        assert fetched.blob_hash == child_blob_hash
        assert fetched.author == "user-1"
        assert fetched.message == "second commit"


def test_create_branch_and_get_branch_head():
    artifact_id = str(uuid.uuid4())
    branch_name = f"main-{uuid.uuid4()}"

    with get_session() as session:
        blob_hash = create_blob(session, f"branch content {uuid.uuid4()}")
        commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=blob_hash,
            parent_ids=[],
            author="user-1",
            message="initial commit",
        )

        create_branch(session, artifact_id=artifact_id, name=branch_name, head_commit_id=commit_id)

        assert get_branch_head(session, artifact_id=artifact_id, name=branch_name) == commit_id


def test_get_branch_head_returns_none_for_missing_branch():
    artifact_id = str(uuid.uuid4())

    with get_session() as session:
        assert get_branch_head(session, artifact_id=artifact_id, name="does-not-exist") is None
```

- [ ] **Step 2: Run the test and confirm it fails**

Command: `cd backend && pytest tests/versioning/test_dag_store.py -v`

Expected failure, because `create_branch` and `get_branch_head` are not defined yet:

```
ImportError: cannot import name 'create_branch' from 'app.versioning.dag_store'
```

- [ ] **Step 3: Implement create_branch and get_branch_head**

Update `backend/app/versioning/dag_store.py`:

```python
import hashlib
import uuid

from app.db.models import Blob, Branch, Commit


def create_blob(session, content: str) -> str:
    blob_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    existing = session.get(Blob, blob_hash)
    if existing is None:
        blob = Blob(hash=blob_hash, content=content, size=len(content.encode("utf-8")))
        session.add(blob)
        session.commit()
    return blob_hash


def get_blob_content(session, blob_hash: str) -> str:
    blob = session.get(Blob, blob_hash)
    if blob is None:
        raise ValueError(f"blob not found for hash {blob_hash}")
    return blob.content


def create_commit(
    session,
    artifact_id: str,
    blob_hash: str,
    parent_ids: list,
    author: str,
    message: str,
) -> str:
    commit_id = str(uuid.uuid4())
    commit = Commit(
        id=commit_id,
        artifact_id=artifact_id,
        parent_ids=parent_ids,
        blob_hash=blob_hash,
        author=author,
        message=message,
    )
    session.add(commit)
    session.commit()
    return commit_id


def get_commit(session, commit_id: str) -> Commit:
    commit = session.get(Commit, commit_id)
    if commit is None:
        raise ValueError(f"commit not found for id {commit_id}")
    return commit


def create_branch(session, artifact_id: str, name: str, head_commit_id: str) -> None:
    branch = Branch(
        id=str(uuid.uuid4()),
        artifact_id=artifact_id,
        name=name,
        head_commit_id=head_commit_id,
    )
    session.add(branch)
    session.commit()


def get_branch_head(session, artifact_id: str, name: str) -> str:
    branch = (
        session.query(Branch)
        .filter_by(artifact_id=artifact_id, name=name)
        .one_or_none()
    )
    if branch is None:
        return None
    return branch.head_commit_id
```

- [ ] **Step 4: Run the test and confirm it passes**

Command: `cd backend && pytest tests/versioning/test_dag_store.py -v`

Expected output: `4 passed`

- [ ] **Step 5: Commit the branch pointer layer**

```bash
git add backend/app/versioning/dag_store.py backend/tests/versioning/test_dag_store.py
git commit -m "Add branch creation and head lookup to the DAG store"
```

- [ ] **Step 6: Write a failing test for updating a branch head**

Extend `backend/tests/versioning/test_dag_store.py`, adding `update_branch_head` to the import list and a new test that moves a branch head forward to a second commit:

```python
from app.versioning.dag_store import (
    create_blob,
    get_blob_content,
    create_commit,
    get_commit,
    create_branch,
    get_branch_head,
    update_branch_head,
)
```

```python
def test_update_branch_head_updates_pointer():
    artifact_id = str(uuid.uuid4())
    branch_name = f"main-{uuid.uuid4()}"

    with get_session() as session:
        first_blob_hash = create_blob(session, f"first content {uuid.uuid4()}")
        first_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=first_blob_hash,
            parent_ids=[],
            author="user-1",
            message="first commit",
        )
        create_branch(session, artifact_id=artifact_id, name=branch_name, head_commit_id=first_commit_id)

        second_blob_hash = create_blob(session, f"second content {uuid.uuid4()}")
        second_commit_id = create_commit(
            session,
            artifact_id=artifact_id,
            blob_hash=second_blob_hash,
            parent_ids=[first_commit_id],
            author="user-1",
            message="second commit",
        )

        update_branch_head(session, artifact_id=artifact_id, name=branch_name, new_commit_id=second_commit_id)

        assert get_branch_head(session, artifact_id=artifact_id, name=branch_name) == second_commit_id
```

- [ ] **Step 7: Run the test and confirm it fails**

Command: `cd backend && pytest tests/versioning/test_dag_store.py -v`

Expected failure, because `update_branch_head` is not defined yet:

```
ImportError: cannot import name 'update_branch_head' from 'app.versioning.dag_store'
```

- [ ] **Step 8: Implement update_branch_head**

Append to `backend/app/versioning/dag_store.py`:

```python
def update_branch_head(session, artifact_id: str, name: str, new_commit_id: str) -> None:
    branch = (
        session.query(Branch)
        .filter_by(artifact_id=artifact_id, name=name)
        .one_or_none()
    )
    if branch is None:
        raise ValueError(f"branch '{name}' not found for artifact {artifact_id}")
    branch.head_commit_id = new_commit_id
    session.commit()
```

- [ ] **Step 9: Run the test and confirm it passes**

Command: `cd backend && pytest tests/versioning/test_dag_store.py -v`

Expected output: `5 passed`

- [ ] **Step 10: Commit the branch head update**

```bash
git add backend/app/versioning/dag_store.py backend/tests/versioning/test_dag_store.py
git commit -m "Add branch head update to the DAG store"
```

### Task 5: Diff Engine (paragraph/message tokenization and generic token diff)

**Files:**
- Create: backend/app/versioning/diff_engine.py
- Test: backend/tests/versioning/test_diff_engine.py

**Interfaces:**
- Consumes: none. This task has no dependency on earlier tasks, the database, or any other module in the codebase; it uses only the Python standard library (`re`, `json`, `difflib`).
- Produces: `tokenize_paragraphs(text: str) -> list[str]`, `tokenize_messages(content_json: str) -> list[str]`, `diff_tokens(tokens_a: list[str], tokens_b: list[str]) -> list[dict]`, `diff_words(text_a: str, text_b: str) -> list[dict]`. Later tasks (diff API endpoints, chat/doc diff views) import these four names directly from `app.versioning.diff_engine`.

- [ ] **Step 1: Write a failing test for tokenize_paragraphs**

Create the directory `backend/tests/versioning/` if it does not already exist, and create `backend/tests/versioning/test_diff_engine.py` with:

```python
from app.versioning.diff_engine import tokenize_paragraphs


def test_tokenize_paragraphs_splits_three_paragraphs():
    text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
    assert tokenize_paragraphs(text) == [
        "First paragraph here.",
        "Second paragraph here.",
        "Third paragraph here.",
    ]
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
cd backend && python -m pytest tests/versioning/test_diff_engine.py -v
```

Expected failure, because neither the `app.versioning` package nor `diff_engine.py` exist yet:

```
E   ModuleNotFoundError: No module named 'app.versioning'
```

- [ ] **Step 3: Write the minimal implementation of tokenize_paragraphs**

Create `backend/app/versioning/__init__.py` as an empty file so `app.versioning` is a package. Create `backend/app/versioning/diff_engine.py` with:

```python
import re


def tokenize_paragraphs(text: str) -> list[str]:
    raw_tokens = re.split(r"\n\s*\n", text)
    return [token.strip() for token in raw_tokens if token.strip()]
```

- [ ] **Step 4: Run the test again and confirm it passes**

Run:

```bash
cd backend && python -m pytest tests/versioning/test_diff_engine.py -v
```

Expected output ends with `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/versioning/__init__.py backend/app/versioning/diff_engine.py backend/tests/versioning/test_diff_engine.py
git commit -m "Add tokenize_paragraphs for paragraph-level diff tokenization"
```

- [ ] **Step 6: Write a failing test for tokenize_messages**

Update the top of `backend/tests/versioning/test_diff_engine.py` to add the new import and append a new test, so the file reads:

```python
import json

from app.versioning.diff_engine import tokenize_messages, tokenize_paragraphs


def test_tokenize_paragraphs_splits_three_paragraphs():
    text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
    assert tokenize_paragraphs(text) == [
        "First paragraph here.",
        "Second paragraph here.",
        "Third paragraph here.",
    ]


def test_tokenize_messages_formats_role_and_text():
    content_json = json.dumps([
        {"role": "user", "text": "hello there", "ts": 1},
        {"role": "assistant", "text": "hi back", "ts": 2},
    ])
    assert tokenize_messages(content_json) == [
        "user: hello there",
        "assistant: hi back",
    ]
```

- [ ] **Step 7: Run the test and confirm it fails**

Run:

```bash
cd backend && python -m pytest tests/versioning/test_diff_engine.py -v
```

Expected failure, because `tokenize_messages` is not yet defined in `diff_engine.py`:

```
E   ImportError: cannot import name 'tokenize_messages' from 'app.versioning.diff_engine'
```

- [ ] **Step 8: Write the minimal implementation of tokenize_messages**

Add `import json` above `import re` at the top of `backend/app/versioning/diff_engine.py`, and append:

```python
def tokenize_messages(content_json: str) -> list[str]:
    messages = json.loads(content_json)
    return [f"{message['role']}: {message['text']}" for message in messages]
```

- [ ] **Step 9: Run the test again and confirm it passes**

Run:

```bash
cd backend && python -m pytest tests/versioning/test_diff_engine.py -v
```

Expected output ends with `2 passed`.

- [ ] **Step 10: Commit**

```bash
git add backend/app/versioning/diff_engine.py backend/tests/versioning/test_diff_engine.py
git commit -m "Add tokenize_messages for chat message diff tokenization"
```

- [ ] **Step 11: Write a failing test for diff_tokens**

Update the import line in `backend/tests/versioning/test_diff_engine.py` to `from app.versioning.diff_engine import diff_tokens, tokenize_messages, tokenize_paragraphs`, and append:

```python
def test_diff_tokens_added_removed_and_changed():
    tokens_a = [
        "Intro paragraph.",
        "Middle paragraph one.",
        "Middle paragraph two.",
        "Closing paragraph.",
    ]
    tokens_b = [
        "Intro paragraph.",
        "Middle paragraph one changed.",
        "Closing paragraph.",
        "New appended paragraph.",
    ]
    result = diff_tokens(tokens_a, tokens_b)
    kinds = [entry["kind"] for entry in result]
    assert kinds == ["unchanged", "changed", "removed", "unchanged", "added"]
```

- [ ] **Step 12: Run the test and confirm it fails**

Run:

```bash
cd backend && python -m pytest tests/versioning/test_diff_engine.py -v
```

Expected failure, because `diff_tokens` is not yet defined:

```
E   ImportError: cannot import name 'diff_tokens' from 'app.versioning.diff_engine'
```

- [ ] **Step 13: Write the minimal implementation of diff_tokens**

Add `import difflib` at the top of `backend/app/versioning/diff_engine.py` (alongside `import json` and `import re`), and append:

```python
def diff_tokens(tokens_a: list[str], tokens_b: list[str]) -> list[dict]:
    matcher = difflib.SequenceMatcher(a=tokens_a, b=tokens_b, autojunk=False)
    result = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for token in tokens_a[i1:i2]:
                result.append({"kind": "unchanged", "text": token, "old_text": None})
        elif tag == "delete":
            for token in tokens_a[i1:i2]:
                result.append({"kind": "removed", "text": token, "old_text": None})
        elif tag == "insert":
            for token in tokens_b[j1:j2]:
                result.append({"kind": "added", "text": token, "old_text": None})
        elif tag == "replace":
            old_tokens = tokens_a[i1:i2]
            new_tokens = tokens_b[j1:j2]
            pair_count = min(len(old_tokens), len(new_tokens))
            for index in range(pair_count):
                result.append({
                    "kind": "changed",
                    "text": new_tokens[index],
                    "old_text": old_tokens[index],
                })
            for token in old_tokens[pair_count:]:
                result.append({"kind": "removed", "text": token, "old_text": None})
            for token in new_tokens[pair_count:]:
                result.append({"kind": "added", "text": token, "old_text": None})
    return result
```

- [ ] **Step 14: Run the test again and confirm it passes**

Run:

```bash
cd backend && python -m pytest tests/versioning/test_diff_engine.py -v
```

Expected output ends with `3 passed`.

- [ ] **Step 15: Commit**

```bash
git add backend/app/versioning/diff_engine.py backend/tests/versioning/test_diff_engine.py
git commit -m "Add diff_tokens generic Myers diff over token lists"
```

- [ ] **Step 16: Write a failing test for diff_words**

Update the import line in `backend/tests/versioning/test_diff_engine.py` to `from app.versioning.diff_engine import diff_tokens, diff_words, tokenize_messages, tokenize_paragraphs`, and append:

```python
def test_diff_words_shows_added_and_removed_words():
    text_a = "the quick brown fox jumps over the lazy dog"
    text_b = "the quick brown fox jumps swiftly over the dog"
    result = diff_words(text_a, text_b)
    kinds = [entry["kind"] for entry in result]
    assert "added" in kinds
    assert "removed" in kinds
```

- [ ] **Step 17: Run the test and confirm it fails**

Run:

```bash
cd backend && python -m pytest tests/versioning/test_diff_engine.py -v
```

Expected failure, because `diff_words` is not yet defined:

```
E   ImportError: cannot import name 'diff_words' from 'app.versioning.diff_engine'
```

- [ ] **Step 18: Write the minimal implementation of diff_words**

Append to `backend/app/versioning/diff_engine.py`:

```python
def diff_words(text_a: str, text_b: str) -> list[dict]:
    words_a = text_a.split()
    words_b = text_b.split()
    return diff_tokens(words_a, words_b)
```

- [ ] **Step 19: Run the test again and confirm it passes**

Run:

```bash
cd backend && python -m pytest tests/versioning/test_diff_engine.py -v
```

Expected output ends with `4 passed`.

- [ ] **Step 20: Commit**

```bash
git add backend/app/versioning/diff_engine.py backend/tests/versioning/test_diff_engine.py
git commit -m "Add diff_words nested word-level diff for changed tokens"
```

### Task 6: Merge Engine (generic 3-way diff3 merge)

**Files:**
- Create: backend/app/versioning/merge_engine.py
- Test: backend/tests/versioning/test_merge_engine.py

**Interfaces:**
- Consumes: none directly. This task does not call `tokenize_paragraphs`, `tokenize_messages`, `diff_tokens`, or `diff_words` from Task 5; it operates purely on token lists that a caller (a later versioning/merge task) produces by calling those functions first, then passes in as `base_tokens`, `ours_tokens`, and `theirs_tokens`.
- Produces: `diff3_merge(base_tokens: list[str], ours_tokens: list[str], theirs_tokens: list[str]) -> dict` returning `{"merged_tokens": list[str], "conflicts": list[dict]}`, where each conflict dict has keys `position` (int), `base` (str or None), `ours` (str or None), `theirs` (str or None). Later tasks (merge API endpoint, conflict-resolution UI, merge-request flow) call this exact function and rely on this exact return shape.

- [ ] **Step 1: Write a failing test for the non-overlapping merge case**

Create the directory `backend/tests/versioning/` if it does not already exist (it will already exist after Task 5), and create `backend/tests/versioning/test_merge_engine.py` with:

```python
from app.versioning.merge_engine import diff3_merge


def test_diff3_merge_non_overlapping_changes():
    base_tokens = [
        "Paragraph one original.",
        "Paragraph two original.",
        "Paragraph three original.",
    ]
    ours_tokens = [
        "Paragraph one changed by ours.",
        "Paragraph two original.",
        "Paragraph three original.",
    ]
    theirs_tokens = [
        "Paragraph one original.",
        "Paragraph two original.",
        "Paragraph three changed by theirs.",
    ]
    result = diff3_merge(base_tokens, ours_tokens, theirs_tokens)
    assert result["merged_tokens"] == [
        "Paragraph one changed by ours.",
        "Paragraph two original.",
        "Paragraph three changed by theirs.",
    ]
    assert result["conflicts"] == []
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
cd backend && python -m pytest tests/versioning/test_merge_engine.py -v
```

Expected failure, because `merge_engine.py` does not exist yet:

```
E   ModuleNotFoundError: No module named 'app.versioning.merge_engine'
```

- [ ] **Step 3: Write the minimal implementation handling one-sided changes**

Create `backend/app/versioning/merge_engine.py` with:

```python
import difflib


def _actions_by_base_index(base_tokens, other_tokens):
    matcher = difflib.SequenceMatcher(a=base_tokens, b=other_tokens, autojunk=False)
    actions = {}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset, base_index in enumerate(range(i1, i2)):
                actions[base_index] = ("unchanged", other_tokens[j1 + offset])
        elif tag == "delete":
            for base_index in range(i1, i2):
                actions[base_index] = ("removed", None)
        elif tag == "replace":
            old_len = i2 - i1
            new_len = j2 - j1
            pair_count = min(old_len, new_len)
            for offset in range(pair_count):
                base_index = i1 + offset
                actions[base_index] = ("changed", other_tokens[j1 + offset])
            for base_index in range(i1 + pair_count, i2):
                actions[base_index] = ("removed", None)
    return actions


def diff3_merge(base_tokens, ours_tokens, theirs_tokens):
    ours_actions = _actions_by_base_index(base_tokens, ours_tokens)
    theirs_actions = _actions_by_base_index(base_tokens, theirs_tokens)

    merged_tokens = []
    conflicts = []

    for base_index, base_text in enumerate(base_tokens):
        ours_action, ours_text = ours_actions.get(base_index, ("unchanged", base_text))
        theirs_action, theirs_text = theirs_actions.get(base_index, ("unchanged", base_text))

        if ours_action == "unchanged" and theirs_action == "unchanged":
            merged_tokens.append(base_text)
        elif ours_action == "unchanged":
            if theirs_action == "changed":
                merged_tokens.append(theirs_text)
        elif theirs_action == "unchanged":
            if ours_action == "changed":
                merged_tokens.append(ours_text)
        else:
            if ours_action == "changed":
                merged_tokens.append(ours_text)
            elif theirs_action == "changed":
                merged_tokens.append(theirs_text)

    return {"merged_tokens": merged_tokens, "conflicts": conflicts}
```

This version aligns base against ours and base against theirs independently, and for any base position where only one side changed, applies that side. It does not yet distinguish a genuine conflict from a coincidental overlap; that gap is closed in Step 8.

- [ ] **Step 4: Run the test again and confirm it passes**

Run:

```bash
cd backend && python -m pytest tests/versioning/test_merge_engine.py -v
```

Expected output ends with `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/versioning/merge_engine.py backend/tests/versioning/test_merge_engine.py
git commit -m "Add diff3_merge non-conflicting three-way merge for paragraph tokens"
```

- [ ] **Step 6: Write a failing test for the overlapping conflict case**

Append to `backend/tests/versioning/test_merge_engine.py`:

```python
def test_diff3_merge_overlapping_changes_produce_conflict():
    base_tokens = [
        "Paragraph one original.",
        "Paragraph two original.",
        "Paragraph three original.",
    ]
    ours_tokens = [
        "Paragraph one original.",
        "Paragraph two changed by ours.",
        "Paragraph three original.",
    ]
    theirs_tokens = [
        "Paragraph one original.",
        "Paragraph two changed by theirs.",
        "Paragraph three original.",
    ]
    result = diff3_merge(base_tokens, ours_tokens, theirs_tokens)
    assert len(result["conflicts"]) == 1
    conflict = result["conflicts"][0]
    assert conflict["position"] == 1
    assert conflict["base"] == "Paragraph two original."
    assert conflict["ours"] == "Paragraph two changed by ours."
    assert conflict["theirs"] == "Paragraph two changed by theirs."
    # merged_tokens keeps a placeholder at the conflict's position so a caller
    # can resolve it later via merged_tokens[conflict["position"]] = resolved_text.
    assert result["merged_tokens"][conflict["position"]] == "Paragraph two original."
```

- [ ] **Step 7: Run the test and confirm it fails**

Run:

```bash
cd backend && python -m pytest tests/versioning/test_merge_engine.py -v
```

Expected failure, because the Step 3 implementation silently applies `ours` at position 1 instead of recording a conflict, so `conflicts` stays empty:

```
>       assert len(result["conflicts"]) == 1
E       assert 0 == 1
E        +  where 0 = len([])
```

- [ ] **Step 8: Extend the implementation to detect and report conflicts instead of guessing**

Replace the contents of `backend/app/versioning/merge_engine.py` with:

```python
import difflib


def _actions_by_base_index(base_tokens, other_tokens):
    matcher = difflib.SequenceMatcher(a=base_tokens, b=other_tokens, autojunk=False)
    actions = {}
    insertions = {}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset, base_index in enumerate(range(i1, i2)):
                actions[base_index] = ("unchanged", other_tokens[j1 + offset])
        elif tag == "delete":
            for base_index in range(i1, i2):
                actions[base_index] = ("removed", None)
        elif tag == "insert":
            insertions.setdefault(i1, []).extend(other_tokens[j1:j2])
        elif tag == "replace":
            old_len = i2 - i1
            new_len = j2 - j1
            pair_count = min(old_len, new_len)
            for offset in range(pair_count):
                base_index = i1 + offset
                actions[base_index] = ("changed", other_tokens[j1 + offset])
            for base_index in range(i1 + pair_count, i2):
                actions[base_index] = ("removed", None)
            if new_len > pair_count:
                insertions.setdefault(i1 + pair_count, []).extend(other_tokens[j1 + pair_count:j2])
    return actions, insertions


def diff3_merge(base_tokens, ours_tokens, theirs_tokens):
    ours_actions, ours_insertions = _actions_by_base_index(base_tokens, ours_tokens)
    theirs_actions, theirs_insertions = _actions_by_base_index(base_tokens, theirs_tokens)

    merged_tokens = []
    conflicts = []

    for base_index, base_text in enumerate(base_tokens):
        for token in ours_insertions.get(base_index, []):
            merged_tokens.append(token)
        for token in theirs_insertions.get(base_index, []):
            if token not in ours_insertions.get(base_index, []):
                merged_tokens.append(token)

        ours_action, ours_text = ours_actions.get(base_index, ("unchanged", base_text))
        theirs_action, theirs_text = theirs_actions.get(base_index, ("unchanged", base_text))

        if ours_action == "unchanged" and theirs_action == "unchanged":
            merged_tokens.append(base_text)
        elif ours_action == "unchanged" and theirs_action != "unchanged":
            if theirs_action == "changed":
                merged_tokens.append(theirs_text)
        elif theirs_action == "unchanged" and ours_action != "unchanged":
            if ours_action == "changed":
                merged_tokens.append(ours_text)
        else:
            if ours_action == theirs_action and ours_text == theirs_text:
                if ours_action == "changed":
                    merged_tokens.append(ours_text)
            else:
                # position must be the actual index the placeholder will occupy
                # in merged_tokens, not base_index — insertions or removals at
                # any earlier base position make those two diverge. Capturing
                # len(merged_tokens) right before appending the placeholder is
                # what keeps merged_tokens[position] valid for callers (e.g. the
                # merge-request flow) that resolve a conflict by overwriting
                # merged_tokens[position] with the resolved text.
                position = len(merged_tokens)
                merged_tokens.append(base_text)
                conflicts.append({
                    "position": position,
                    "base": base_text,
                    "ours": ours_text if ours_action == "changed" else None,
                    "theirs": theirs_text if theirs_action == "changed" else None,
                })

    trailing_index = len(base_tokens)
    for token in ours_insertions.get(trailing_index, []):
        merged_tokens.append(token)
    for token in theirs_insertions.get(trailing_index, []):
        if token not in ours_insertions.get(trailing_index, []):
            merged_tokens.append(token)

    return {"merged_tokens": merged_tokens, "conflicts": conflicts}
```

This version adds two things the Step 3 version lacked: tracking of pure insertions on each side (tokens with no corresponding base position), and, when both sides change the same base position, a comparison between the two resulting texts — identical changes are applied once, and differing changes are emitted as a conflict record rather than one side being picked silently.

- [ ] **Step 9: Run the test again and confirm both tests pass**

Run:

```bash
cd backend && python -m pytest tests/versioning/test_merge_engine.py -v
```

Expected output ends with `2 passed`.

- [ ] **Step 10: Commit**

```bash
git add backend/app/versioning/merge_engine.py backend/tests/versioning/test_merge_engine.py
git commit -m "Add conflict detection to diff3_merge for overlapping edits"
```

### Task 7: VersionedArtifact Interface and DAG Adapter

**Files:**
- Create: backend/app/versioning/interface.py
- Create: backend/app/versioning/dag_adapter.py
- Test: backend/tests/versioning/test_interface.py
- Test: backend/tests/versioning/test_dag_adapter.py

**Interfaces:**
- Consumes: `create_blob(session, content)`, `get_blob_content(session, blob_hash)`, `create_commit(session, artifact_id, blob_hash, parent_ids, author, message)`, `get_commit(session, commit_id)`, `create_branch(session, artifact_id, name, head_commit_id)`, `get_branch_head(session, artifact_id, name)`, `update_branch_head(session, artifact_id, name, new_commit_id)` from `app.versioning.dag_store`; `tokenize_paragraphs(text)`, `tokenize_messages(content_json)`, `diff_tokens(tokens_a, tokens_b)`, `diff_words(text_a, text_b)` from `app.versioning.diff_engine`; `diff3_merge(base_tokens, ours_tokens, theirs_tokens)` from `app.versioning.merge_engine`. Assumes, per the DAG schema in the design doc, that `create_commit` and `get_commit` return an object exposing `.id` and `.blob_hash` attributes, and that `get_branch_head` returns `None` when no branch with that name exists on the artifact.
- Produces: `VersionedArtifact` (a runtime-checkable Protocol) from `backend/app/versioning/interface.py`. `DagVersionedArtifact(session, artifact_id, tokenizer)` from `backend/app/versioning/dag_adapter.py` with methods `commit(content, author, message, parent_ref)`, `diff(ref_a, ref_b)`, `branch(name, from_ref)`, `merge(base_ref, ours_ref, theirs_ref)`, `get_content(ref)`, `branch_head(name)`.

- [ ] **Step 1: Write a failing test for the VersionedArtifact protocol**

Create `backend/tests/versioning/test_interface.py`:

```python
import pytest

from app.versioning.interface import VersionedArtifact


def test_versioned_artifact_protocol_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        VersionedArtifact()


def test_object_implementing_all_methods_satisfies_the_protocol():
    class CompleteArtifact:
        def commit(self, content, author, message, parent_ref):
            return "commit-1"

        def diff(self, ref_a, ref_b):
            return []

        def branch(self, name, from_ref):
            return None

        def merge(self, base_ref, ours_ref, theirs_ref):
            return {"conflicts": [], "merged": []}

        def get_content(self, ref):
            return "content"

        def branch_head(self, name):
            return "commit-1"

    assert isinstance(CompleteArtifact(), VersionedArtifact)


def test_object_missing_a_method_does_not_satisfy_the_protocol():
    class IncompleteArtifact:
        def commit(self, content, author, message, parent_ref):
            return "commit-1"

    assert not isinstance(IncompleteArtifact(), VersionedArtifact)
```

- [ ] **Step 2: Run and confirm the test fails**

Command: `cd backend && python -m pytest tests/versioning/test_interface.py -v`

Expected failure, because `app/versioning/interface.py` does not exist yet:

```
ImportError while importing test module '.../tests/versioning/test_interface.py'.
...
E   ModuleNotFoundError: No module named 'app.versioning.interface'
```

- [ ] **Step 3: Implement the VersionedArtifact protocol**

Create `backend/app/versioning/interface.py`:

```python
"""Common interface unifying the custom DAG and git-backed versioning engines.

Both DagVersionedArtifact (docs, chat exports, PDFs) and a future
GitVersionedArtifact (codebase artifacts) implement this same interface so
ingestion, retrieval, provenance, multi-agent PRs, and the UI can call
commit(), diff(), branch(), merge(), get_content(), and branch_head() without
knowing which backend a given artifact uses.

This is defined as a typing.Protocol rather than an abc.ABC on purpose: a
Protocol is structural (isinstance checks work off matching method names, not
explicit inheritance) and, unlike an ABC with @abstractmethod, subclassing it
directly does not block instantiation of a class that only implements some of
the methods so far. That property is relied on while DagVersionedArtifact is
built up incrementally, method by method, in the tests below.
"""

from typing import Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class VersionedArtifact(Protocol):
    def commit(
        self,
        content: str,
        author: str,
        message: str,
        parent_ref: Optional[str],
    ) -> str:
        ...

    def diff(self, ref_a: str, ref_b: str) -> List[Dict]:
        ...

    def branch(self, name: str, from_ref: str) -> None:
        ...

    def merge(self, base_ref: str, ours_ref: str, theirs_ref: str) -> Dict:
        ...

    def get_content(self, ref: str) -> str:
        ...

    def branch_head(self, name: str) -> str:
        ...
```

- [ ] **Step 4: Run and confirm the test passes**

Command: `cd backend && python -m pytest tests/versioning/test_interface.py -v`

Expected output: `3 passed`.

- [ ] **Step 5: Commit the interface**

```
git add backend/app/versioning/interface.py backend/tests/versioning/test_interface.py
git commit -m "Add VersionedArtifact protocol unifying DAG and git versioning backends"
```

- [ ] **Step 6: Write a failing test for DagVersionedArtifact commit and get_content**

Create `backend/tests/versioning/test_dag_adapter.py`. The `db_session` fixture below is the shared pytest fixture introduced in Task 2: it yields a SQLAlchemy Session bound to the real Postgres test database and rolls its changes back after each test, so nothing here creates a new database connection strategy.

```python
import uuid

import pytest
from sqlalchemy import text

from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.diff_engine import tokenize_paragraphs


@pytest.fixture
def artifact_id(db_session):
    new_id = str(uuid.uuid4())
    db_session.execute(
        text(
            "INSERT INTO artifact (id, workspace_id, type, name) "
            "VALUES (:id, :workspace_id, :type, :name)"
        ),
        {
            "id": new_id,
            "workspace_id": str(uuid.uuid4()),
            "type": "doc",
            "name": "Adapter Test Artifact",
        },
    )
    db_session.commit()
    return new_id


def test_first_commit_is_readable_via_get_content(db_session, artifact_id):
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    commit_id = artifact.commit(
        content="Paragraph one.\n\nParagraph two.",
        author="user-1",
        message="initial import",
        parent_ref=None,
    )
    assert isinstance(commit_id, str)
    assert artifact.get_content(commit_id) == "Paragraph one.\n\nParagraph two."
```

- [ ] **Step 7: Run and confirm the test fails**

Command: `cd backend && python -m pytest tests/versioning/test_dag_adapter.py -v`

Expected failure, because `app/versioning/dag_adapter.py` does not exist yet:

```
ImportError while importing test module '.../tests/versioning/test_dag_adapter.py'.
...
E   ModuleNotFoundError: No module named 'app.versioning.dag_adapter'
```

- [ ] **Step 8: Implement DagVersionedArtifact constructor, commit, and get_content**

Create `backend/app/versioning/dag_adapter.py`:

```python
from typing import Callable, Dict, List, Optional

from app.versioning.dag_store import (
    create_blob,
    create_commit,
    get_blob_content,
    get_branch_head,
    get_commit,
)
from app.versioning.interface import VersionedArtifact


class DagVersionedArtifact(VersionedArtifact):
    def __init__(self, session, artifact_id: str, tokenizer: Callable[[str], List[str]]):
        self.session = session
        self.artifact_id = artifact_id
        self.tokenizer = tokenizer

    def commit(
        self,
        content: str,
        author: str,
        message: str,
        parent_ref: Optional[str],
    ) -> str:
        blob_hash = create_blob(self.session, content)
        parent_ids = [parent_ref] if parent_ref else []
        commit = create_commit(
            self.session, self.artifact_id, blob_hash, parent_ids, author, message
        )
        return commit.id

    def get_content(self, ref: str) -> str:
        commit_id = self._resolve_commit_id(ref)
        commit = get_commit(self.session, commit_id)
        return get_blob_content(self.session, commit.blob_hash)

    def _resolve_commit_id(self, ref: str) -> str:
        # `ref` may be a branch name or a direct commit id. Try it as a
        # branch name first; if no such branch exists on this artifact, fall
        # back to treating it as a commit id directly.
        branch_head_id = get_branch_head(self.session, self.artifact_id, ref)
        if branch_head_id is not None:
            return branch_head_id
        return ref
```

- [ ] **Step 9: Run and confirm the test passes**

Command: `cd backend && python -m pytest tests/versioning/test_dag_adapter.py -v`

Expected output: `1 passed`.

- [ ] **Step 10: Commit the constructor, commit, and get_content methods**

```
git add backend/app/versioning/dag_adapter.py backend/tests/versioning/test_dag_adapter.py
git commit -m "Add DagVersionedArtifact commit and get_content backed by dag_store"
```

- [ ] **Step 11: Write a failing test for branch and branch_head**

Append to `backend/tests/versioning/test_dag_adapter.py`:

```python
def test_branch_head_resolves_to_the_commit_it_was_created_from(db_session, artifact_id):
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    commit_id = artifact.commit("Paragraph one.\n\nParagraph two.", "user-1", "init", None)
    artifact.branch("feature", commit_id)
    assert artifact.branch_head("feature") == commit_id
    assert artifact.get_content("feature") == "Paragraph one.\n\nParagraph two."
```

- [ ] **Step 12: Run and confirm the test fails**

Command: `cd backend && python -m pytest tests/versioning/test_dag_adapter.py::test_branch_head_resolves_to_the_commit_it_was_created_from -v`

Expected failure. Because `VersionedArtifact` is a Protocol, `DagVersionedArtifact` at this point still structurally satisfies it through inherited no-op stub methods for `branch` and `branch_head` rather than raising `AttributeError`, so the failure is an assertion mismatch:

```
    artifact.branch("feature", commit_id)
>   assert artifact.branch_head("feature") == commit_id
E   AssertionError: assert None == '<the commit_id uuid>'
E    +  where None = branch_head('feature')
```

- [ ] **Step 13: Implement branch and branch_head**

Update `backend/app/versioning/dag_adapter.py`:

```python
from typing import Callable, Dict, List, Optional

from app.versioning.dag_store import (
    create_blob,
    create_branch,
    create_commit,
    get_blob_content,
    get_branch_head,
    get_commit,
)
from app.versioning.interface import VersionedArtifact


class DagVersionedArtifact(VersionedArtifact):
    def __init__(self, session, artifact_id: str, tokenizer: Callable[[str], List[str]]):
        self.session = session
        self.artifact_id = artifact_id
        self.tokenizer = tokenizer

    def commit(
        self,
        content: str,
        author: str,
        message: str,
        parent_ref: Optional[str],
    ) -> str:
        blob_hash = create_blob(self.session, content)
        parent_ids = [parent_ref] if parent_ref else []
        commit = create_commit(
            self.session, self.artifact_id, blob_hash, parent_ids, author, message
        )
        return commit.id

    def branch(self, name: str, from_ref: str) -> None:
        commit_id = self._resolve_commit_id(from_ref)
        create_branch(self.session, self.artifact_id, name, commit_id)

    def get_content(self, ref: str) -> str:
        commit_id = self._resolve_commit_id(ref)
        commit = get_commit(self.session, commit_id)
        return get_blob_content(self.session, commit.blob_hash)

    def branch_head(self, name: str) -> str:
        return get_branch_head(self.session, self.artifact_id, name)

    def _resolve_commit_id(self, ref: str) -> str:
        branch_head_id = get_branch_head(self.session, self.artifact_id, ref)
        if branch_head_id is not None:
            return branch_head_id
        return ref
```

- [ ] **Step 14: Run and confirm the test passes**

Command: `cd backend && python -m pytest tests/versioning/test_dag_adapter.py -v`

Expected output: `2 passed`.

- [ ] **Step 15: Commit the branch and branch_head methods**

```
git add backend/app/versioning/dag_adapter.py backend/tests/versioning/test_dag_adapter.py
git commit -m "Add DagVersionedArtifact branch and branch_head"
```

- [ ] **Step 16: Write a failing test for diff with word_diff on changed paragraphs**

Append to `backend/tests/versioning/test_dag_adapter.py`:

```python
def test_diff_of_a_changed_paragraph_includes_word_diff(db_session, artifact_id):
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    c1 = artifact.commit("Paragraph one.\n\nParagraph two.", "user-1", "init", None)
    c2 = artifact.commit(
        "Paragraph one.\n\nParagraph two updated.", "user-1", "edit", c1
    )
    entries = artifact.diff(c1, c2)
    changed = [entry for entry in entries if entry["type"] == "change"]
    assert len(changed) == 1
    assert changed[0]["old_text"] == "Paragraph two."
    assert changed[0]["text"] == "Paragraph two updated."
    assert "word_diff" in changed[0]
    assert changed[0]["word_diff"]
```

- [ ] **Step 17: Run and confirm the test fails**

Command: `cd backend && python -m pytest tests/versioning/test_dag_adapter.py::test_diff_of_a_changed_paragraph_includes_word_diff -v`

Expected failure, because `diff` is still an inherited no-op stub that returns `None`:

```
    entries = artifact.diff(c1, c2)
>   changed = [entry for entry in entries if entry["type"] == "change"]
E   TypeError: 'NoneType' object is not iterable
```

- [ ] **Step 18: Implement diff**

Update `backend/app/versioning/dag_adapter.py`:

```python
from typing import Callable, Dict, List, Optional

from app.versioning.dag_store import (
    create_blob,
    create_branch,
    create_commit,
    get_blob_content,
    get_branch_head,
    get_commit,
)
from app.versioning.diff_engine import diff_tokens, diff_words
from app.versioning.interface import VersionedArtifact


class DagVersionedArtifact(VersionedArtifact):
    def __init__(self, session, artifact_id: str, tokenizer: Callable[[str], List[str]]):
        self.session = session
        self.artifact_id = artifact_id
        self.tokenizer = tokenizer

    def commit(
        self,
        content: str,
        author: str,
        message: str,
        parent_ref: Optional[str],
    ) -> str:
        blob_hash = create_blob(self.session, content)
        parent_ids = [parent_ref] if parent_ref else []
        commit = create_commit(
            self.session, self.artifact_id, blob_hash, parent_ids, author, message
        )
        return commit.id

    def diff(self, ref_a: str, ref_b: str) -> List[Dict]:
        content_a = self.get_content(ref_a)
        content_b = self.get_content(ref_b)
        tokens_a = self.tokenizer(content_a)
        tokens_b = self.tokenizer(content_b)
        entries = diff_tokens(tokens_a, tokens_b)
        for entry in entries:
            if entry.get("type") == "change":
                entry["word_diff"] = diff_words(entry["old_text"], entry["text"])
        return entries

    def branch(self, name: str, from_ref: str) -> None:
        commit_id = self._resolve_commit_id(from_ref)
        create_branch(self.session, self.artifact_id, name, commit_id)

    def get_content(self, ref: str) -> str:
        commit_id = self._resolve_commit_id(ref)
        commit = get_commit(self.session, commit_id)
        return get_blob_content(self.session, commit.blob_hash)

    def branch_head(self, name: str) -> str:
        return get_branch_head(self.session, self.artifact_id, name)

    def _resolve_commit_id(self, ref: str) -> str:
        branch_head_id = get_branch_head(self.session, self.artifact_id, ref)
        if branch_head_id is not None:
            return branch_head_id
        return ref
```

- [ ] **Step 19: Run and confirm the test passes**

Command: `cd backend && python -m pytest tests/versioning/test_dag_adapter.py -v`

Expected output: `3 passed`.

- [ ] **Step 20: Commit diff**

```
git add backend/app/versioning/dag_adapter.py backend/tests/versioning/test_dag_adapter.py
git commit -m "Add DagVersionedArtifact diff with nested word_diff on changed paragraphs"
```

- [ ] **Step 21: Write a failing test for a no-conflict merge that creates a merge commit**

Append to `backend/tests/versioning/test_dag_adapter.py`:

```python
from app.versioning.dag_store import update_branch_head


def test_merge_with_no_conflicts_creates_a_merge_commit_with_both_changes(
    db_session, artifact_id
):
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_paragraphs)
    base_commit = artifact.commit(
        "Paragraph one.\n\nParagraph two.", "user-1", "init", None
    )
    artifact.branch("feature", base_commit)

    branch_commit = artifact.commit(
        "Paragraph one.\n\nParagraph two changed on branch.",
        "user-1",
        "branch edit",
        base_commit,
    )
    update_branch_head(db_session, artifact_id, "feature", branch_commit)

    main_commit = artifact.commit(
        "Paragraph one changed on main.\n\nParagraph two.",
        "user-1",
        "main edit",
        base_commit,
    )

    result = artifact.merge(
        base_ref=base_commit,
        ours_ref=main_commit,
        theirs_ref=artifact.branch_head("feature"),
    )

    assert result["conflicts"] == []
    assert "merge_commit_id" in result
    merged_content = artifact.get_content(result["merge_commit_id"])
    assert "Paragraph one changed on main." in merged_content
    assert "Paragraph two changed on branch." in merged_content
```

- [ ] **Step 22: Run and confirm the test fails**

Command: `cd backend && python -m pytest tests/versioning/test_dag_adapter.py::test_merge_with_no_conflicts_creates_a_merge_commit_with_both_changes -v`

Expected failure, because `merge` is still an inherited no-op stub that returns `None`:

```
    result = artifact.merge(
        base_ref=base_commit,
        ours_ref=main_commit,
        theirs_ref=artifact.branch_head("feature"),
    )
>   assert result["conflicts"] == []
E   TypeError: 'NoneType' object is not subscriptable
```

- [ ] **Step 23: Implement merge for the no-conflict, auto-commit path**

Update `backend/app/versioning/dag_adapter.py`:

```python
from typing import Callable, Dict, List, Optional

from app.versioning.dag_store import (
    create_blob,
    create_branch,
    create_commit,
    get_blob_content,
    get_branch_head,
    get_commit,
)
from app.versioning.diff_engine import diff_tokens, diff_words
from app.versioning.interface import VersionedArtifact
from app.versioning.merge_engine import diff3_merge


class DagVersionedArtifact(VersionedArtifact):
    def __init__(self, session, artifact_id: str, tokenizer: Callable[[str], List[str]]):
        self.session = session
        self.artifact_id = artifact_id
        self.tokenizer = tokenizer

    def commit(
        self,
        content: str,
        author: str,
        message: str,
        parent_ref: Optional[str],
    ) -> str:
        blob_hash = create_blob(self.session, content)
        parent_ids = [parent_ref] if parent_ref else []
        commit = create_commit(
            self.session, self.artifact_id, blob_hash, parent_ids, author, message
        )
        return commit.id

    def diff(self, ref_a: str, ref_b: str) -> List[Dict]:
        content_a = self.get_content(ref_a)
        content_b = self.get_content(ref_b)
        tokens_a = self.tokenizer(content_a)
        tokens_b = self.tokenizer(content_b)
        entries = diff_tokens(tokens_a, tokens_b)
        for entry in entries:
            if entry.get("type") == "change":
                entry["word_diff"] = diff_words(entry["old_text"], entry["text"])
        return entries

    def branch(self, name: str, from_ref: str) -> None:
        commit_id = self._resolve_commit_id(from_ref)
        create_branch(self.session, self.artifact_id, name, commit_id)

    def merge(self, base_ref: str, ours_ref: str, theirs_ref: str) -> Dict:
        base_content = self.get_content(base_ref)
        ours_content = self.get_content(ours_ref)
        theirs_content = self.get_content(theirs_ref)
        base_tokens = self.tokenizer(base_content)
        ours_tokens = self.tokenizer(ours_content)
        theirs_tokens = self.tokenizer(theirs_content)
        result = diff3_merge(base_tokens, ours_tokens, theirs_tokens)
        if len(result["conflicts"]) == 0:
            ours_commit_id = self._resolve_commit_id(ours_ref)
            theirs_commit_id = self._resolve_commit_id(theirs_ref)
            merged_content = "\n\n".join(result["merged_tokens"])
            blob_hash = create_blob(self.session, merged_content)
            merge_commit = create_commit(
                self.session,
                self.artifact_id,
                blob_hash,
                [ours_commit_id, theirs_commit_id],
                "merge-bot",
                f"Merge {theirs_ref} into {ours_ref}",
            )
            result["merge_commit_id"] = merge_commit.id
        return result

    def get_content(self, ref: str) -> str:
        commit_id = self._resolve_commit_id(ref)
        commit = get_commit(self.session, commit_id)
        return get_blob_content(self.session, commit.blob_hash)

    def branch_head(self, name: str) -> str:
        return get_branch_head(self.session, self.artifact_id, name)

    def _resolve_commit_id(self, ref: str) -> str:
        branch_head_id = get_branch_head(self.session, self.artifact_id, ref)
        if branch_head_id is not None:
            return branch_head_id
        return ref
```

- [ ] **Step 24: Run and confirm the test passes**

Command: `cd backend && python -m pytest tests/versioning/test_dag_adapter.py -v`

Expected output: `4 passed`.

- [ ] **Step 25: Commit the no-conflict merge path**

```
git add backend/app/versioning/dag_adapter.py backend/tests/versioning/test_dag_adapter.py
git commit -m "Add DagVersionedArtifact merge with auto-commit on zero conflicts"
```

- [ ] **Step 26: Write a failing test that the message tokenizer must not auto-commit a merge**

Append to `backend/tests/versioning/test_dag_adapter.py`:

```python
import json

from app.versioning.diff_engine import tokenize_messages


def tokenize_messages_from_json(content: str):
    return tokenize_messages(json.loads(content))


def test_merge_with_message_tokenizer_does_not_auto_commit(db_session, artifact_id):
    artifact = DagVersionedArtifact(db_session, artifact_id, tokenize_messages_from_json)
    base_json = [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "hello"}]
    ours_json = [
        {"role": "user", "text": "hi there"},
        {"role": "assistant", "text": "hello"},
    ]
    theirs_json = [
        {"role": "user", "text": "hi"},
        {"role": "assistant", "text": "hello friend"},
    ]
    base_commit = artifact.commit(json.dumps(base_json), "user-1", "init", None)
    ours_commit = artifact.commit(json.dumps(ours_json), "user-1", "ours", base_commit)
    theirs_commit = artifact.commit(
        json.dumps(theirs_json), "user-1", "theirs", base_commit
    )

    result = artifact.merge(base_commit, ours_commit, theirs_commit)

    assert result["conflicts"] == []
    assert "merge_commit_id" not in result
```

- [ ] **Step 27: Run and confirm the test fails**

Command: `cd backend && python -m pytest tests/versioning/test_dag_adapter.py::test_merge_with_message_tokenizer_does_not_auto_commit -v`

Expected failure, because the current `merge` implementation auto-commits whenever there are zero conflicts regardless of tokenizer:

```
    result = artifact.merge(base_commit, ours_commit, theirs_commit)

    assert result["conflicts"] == []
>   assert "merge_commit_id" not in result
E   AssertionError: assert 'merge_commit_id' not in {'conflicts': [], 'merge_commit_id': '<uuid>', 'merged': ['user: hi there', 'assistant: hello friend']}
```

- [ ] **Step 28: Restrict auto-commit to the paragraph tokenizer**

Update `backend/app/versioning/dag_adapter.py`:

```python
from typing import Callable, Dict, List, Optional

from app.versioning.dag_store import (
    create_blob,
    create_branch,
    create_commit,
    get_blob_content,
    get_branch_head,
    get_commit,
)
from app.versioning.diff_engine import diff_tokens, diff_words, tokenize_paragraphs
from app.versioning.interface import VersionedArtifact
from app.versioning.merge_engine import diff3_merge


class DagVersionedArtifact(VersionedArtifact):
    def __init__(self, session, artifact_id: str, tokenizer: Callable[[str], List[str]]):
        self.session = session
        self.artifact_id = artifact_id
        self.tokenizer = tokenizer

    def commit(
        self,
        content: str,
        author: str,
        message: str,
        parent_ref: Optional[str],
    ) -> str:
        blob_hash = create_blob(self.session, content)
        parent_ids = [parent_ref] if parent_ref else []
        commit = create_commit(
            self.session, self.artifact_id, blob_hash, parent_ids, author, message
        )
        return commit.id

    def diff(self, ref_a: str, ref_b: str) -> List[Dict]:
        content_a = self.get_content(ref_a)
        content_b = self.get_content(ref_b)
        tokens_a = self.tokenizer(content_a)
        tokens_b = self.tokenizer(content_b)
        entries = diff_tokens(tokens_a, tokens_b)
        for entry in entries:
            if entry.get("type") == "change":
                entry["word_diff"] = diff_words(entry["old_text"], entry["text"])
        return entries

    def branch(self, name: str, from_ref: str) -> None:
        commit_id = self._resolve_commit_id(from_ref)
        create_branch(self.session, self.artifact_id, name, commit_id)

    def merge(self, base_ref: str, ours_ref: str, theirs_ref: str) -> Dict:
        base_content = self.get_content(base_ref)
        ours_content = self.get_content(ours_ref)
        theirs_content = self.get_content(theirs_ref)
        base_tokens = self.tokenizer(base_content)
        ours_tokens = self.tokenizer(ours_content)
        theirs_tokens = self.tokenizer(theirs_content)
        result = diff3_merge(base_tokens, ours_tokens, theirs_tokens)
        # Auto-committing the merge result is only supported when this
        # adapter tokenizes on paragraphs, because the paragraph tokenizer's
        # join separator ("\n\n") round-trips cleanly back into the original
        # text shape. When this adapter is wired up with the message
        # tokenizer instead, this method intentionally stops after
        # diff3_merge and hands the raw result back to the caller, which
        # resolves message merges through the merge_request UI rather than
        # an automatic commit.
        if len(result["conflicts"]) == 0 and self.tokenizer is tokenize_paragraphs:
            ours_commit_id = self._resolve_commit_id(ours_ref)
            theirs_commit_id = self._resolve_commit_id(theirs_ref)
            merged_content = "\n\n".join(result["merged_tokens"])
            blob_hash = create_blob(self.session, merged_content)
            merge_commit = create_commit(
                self.session,
                self.artifact_id,
                blob_hash,
                [ours_commit_id, theirs_commit_id],
                "merge-bot",
                f"Merge {theirs_ref} into {ours_ref}",
            )
            result["merge_commit_id"] = merge_commit.id
        return result

    def get_content(self, ref: str) -> str:
        commit_id = self._resolve_commit_id(ref)
        commit = get_commit(self.session, commit_id)
        return get_blob_content(self.session, commit.blob_hash)

    def branch_head(self, name: str) -> str:
        return get_branch_head(self.session, self.artifact_id, name)

    def _resolve_commit_id(self, ref: str) -> str:
        branch_head_id = get_branch_head(self.session, self.artifact_id, ref)
        if branch_head_id is not None:
            return branch_head_id
        return ref
```

- [ ] **Step 29: Run and confirm the full test file passes**

Command: `cd backend && python -m pytest tests/versioning/test_dag_adapter.py tests/versioning/test_interface.py -v`

Expected output: `8 passed`.

- [ ] **Step 30: Commit the tokenizer-gated merge behavior**

```
git add backend/app/versioning/dag_adapter.py backend/tests/versioning/test_dag_adapter.py
git commit -m "Restrict DagVersionedArtifact merge auto-commit to the paragraph tokenizer"
```

### Task 8: Git-Backed Codebase Adapter

**Files:**
- Create: backend/app/versioning/git_adapter.py
- Test: backend/tests/versioning/test_git_adapter.py

**Interfaces:**
- Consumes: none from earlier tasks. This module depends only on the third-party `pygit2` library and the existing `backend/app` package layout created by the project skeleton task.
- Produces: `init_repo_from_files(repo_path: str, files: dict) -> None`, `clone_repo(source_path_or_url: str, dest_path: str) -> None`, `class GitVersionedArtifact(repo_path: str)` with `commit(files, author: str, message: str) -> str`, `diff(ref_a: str, ref_b: str) -> list`, `branch(name: str, from_ref: str) -> None`, `branch_head(name: str) -> str`, `merge(base_ref: str, ours_ref: str, theirs_ref: str) -> dict`, `get_content(ref: str) -> dict`. Also produces one supplementary helper not required by later tasks but used internally by this task's own tests: `checkout_branch(name: str) -> None`, which switches the working tree and HEAD to a named local branch.

- [ ] **Step 1: Write the failing test for `init_repo_from_files`**

Create `backend/tests/versioning/test_git_adapter.py`:

```python
import os
import tempfile

from app.versioning.git_adapter import init_repo_from_files


def test_init_repo_from_files_creates_initial_commit():
    repo_path = tempfile.mkdtemp()

    init_repo_from_files(repo_path, {"a.txt": "content a\n", "b.txt": "content b\n"})

    assert os.path.isdir(os.path.join(repo_path, ".git"))
    assert open(os.path.join(repo_path, "a.txt")).read() == "content a\n"
    assert open(os.path.join(repo_path, "b.txt")).read() == "content b\n"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.versioning.git_adapter'`

- [ ] **Step 3: Write minimal implementation**

Add `pygit2==1.20.0` to `backend/requirements.txt` (create the file if it does not already exist) and install it with `pip install -r backend/requirements.txt`. Create `backend/app/versioning/git_adapter.py`:

```python
import os

import pygit2


def init_repo_from_files(repo_path: str, files: dict) -> None:
    os.makedirs(repo_path, exist_ok=True)
    repo = pygit2.init_repository(repo_path)
    for path, content in files.items():
        full_path = os.path.join(repo_path, path)
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
    index = repo.index
    index.add_all()
    index.write()
    tree = index.write_tree()
    signature = pygit2.Signature("system", "system@local")
    repo.create_commit("HEAD", signature, signature, "initial commit", tree, [])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/versioning/git_adapter.py backend/tests/versioning/test_git_adapter.py
git commit -m "feat(versioning): create git-backed repos from an initial file set"
```

- [ ] **Step 6: Write the failing test for `clone_repo`**

Append to `backend/tests/versioning/test_git_adapter.py` and change the import line at the top of the file to `from app.versioning.git_adapter import clone_repo, init_repo_from_files`:

```python
def test_clone_repo_preserves_content_and_history():
    source_path = tempfile.mkdtemp()
    init_repo_from_files(source_path, {"readme.md": "hello\n"})

    dest_path = tempfile.mkdtemp()
    clone_repo(source_path, dest_path)

    assert os.path.isdir(os.path.join(dest_path, ".git"))
    assert open(os.path.join(dest_path, "readme.md")).read() == "hello\n"
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: FAIL with `ImportError: cannot import name 'clone_repo' from 'app.versioning.git_adapter'`

- [ ] **Step 8: Write minimal implementation**

Append to `backend/app/versioning/git_adapter.py`:

```python
def clone_repo(source_path_or_url: str, dest_path: str) -> None:
    pygit2.clone_repository(source_path_or_url, dest_path)
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: PASS (2 passed)

- [ ] **Step 10: Commit**

```bash
git add backend/app/versioning/git_adapter.py backend/tests/versioning/test_git_adapter.py
git commit -m "feat(versioning): support cloning existing git repos"
```

- [ ] **Step 11: Write the failing test for `GitVersionedArtifact.commit`**

Append to `backend/tests/versioning/test_git_adapter.py` and change the import line to `from app.versioning.git_adapter import GitVersionedArtifact, clone_repo, init_repo_from_files`:

```python
def test_commit_writes_new_file_and_returns_commit_id():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n"})

    artifact = GitVersionedArtifact(repo_path)
    commit_id = artifact.commit(
        {"a.txt": "content a changed\n"}, "user-1", "edit a"
    )

    assert isinstance(commit_id, str)
    assert len(commit_id) == 40
    assert open(os.path.join(repo_path, "a.txt")).read() == "content a changed\n"
```

- [ ] **Step 12: Run test to verify it fails**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: FAIL with `ImportError: cannot import name 'GitVersionedArtifact' from 'app.versioning.git_adapter'`

- [ ] **Step 13: Write minimal implementation**

Append to `backend/app/versioning/git_adapter.py`:

```python
class GitVersionedArtifact:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.repo = pygit2.Repository(repo_path)

    def commit(self, files, author: str, message: str) -> str:
        if files is not None:
            for path, text in files.items():
                full_path = os.path.join(self.repo_path, path)
                if os.path.dirname(path):
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(text)
        index = self.repo.index
        index.add_all()
        index.write()
        tree = index.write_tree()
        signature = pygit2.Signature(author, f"{author}@local")
        parents = [] if self.repo.head_is_unborn else [self.repo.head.target]
        ref_name = "HEAD" if self.repo.head_is_unborn else self.repo.head.name
        new_commit_id = self.repo.create_commit(
            ref_name, signature, signature, message, tree, parents
        )
        return str(new_commit_id)
```

- [ ] **Step 14: Run test to verify it passes**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: PASS (3 passed)

- [ ] **Step 15: Commit**

```bash
git add backend/app/versioning/git_adapter.py backend/tests/versioning/test_git_adapter.py
git commit -m "feat(versioning): commit files to a GitVersionedArtifact"
```

- [ ] **Step 16: Write the failing test for `diff`**

Append to `backend/tests/versioning/test_git_adapter.py`:

```python
def test_diff_reports_added_removed_and_modified_paths():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(
        repo_path, {"a.txt": "content a\n", "b.txt": "content b\n"}
    )
    artifact = GitVersionedArtifact(repo_path)
    first_commit = artifact.commit(None, "user-1", "noop")

    os.remove(os.path.join(repo_path, "b.txt"))
    second_commit = artifact.commit(
        {"a.txt": "content a changed\n", "c.txt": "content c\n"},
        "user-1",
        "modify a, add c, remove b",
    )

    changes = artifact.diff(first_commit, second_commit)
    changes_by_path = {change["path"]: change["status"] for change in changes}

    assert changes_by_path == {
        "a.txt": "modified",
        "b.txt": "removed",
        "c.txt": "added",
    }
```

- [ ] **Step 17: Run test to verify it fails**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: FAIL with `AttributeError: 'GitVersionedArtifact' object has no attribute 'diff'`

- [ ] **Step 18: Write minimal implementation**

Add the status lookup table near the top of `backend/app/versioning/git_adapter.py`, right after the `import pygit2` line:

```python
_STATUS_MAP = {
    pygit2.GIT_DELTA_ADDED: "added",
    pygit2.GIT_DELTA_DELETED: "removed",
    pygit2.GIT_DELTA_MODIFIED: "modified",
}
```

Add these two methods inside `GitVersionedArtifact`, after `commit`:

```python
    def _resolve_commit(self, ref: str):
        branch = self.repo.branches.local.get(ref)
        if branch is not None:
            return self.repo[branch.target]
        return self.repo[pygit2.Oid(hex=ref)]

    def diff(self, ref_a: str, ref_b: str) -> list:
        commit_a = self._resolve_commit(ref_a)
        commit_b = self._resolve_commit(ref_b)
        tree_diff = self.repo.diff(commit_a.tree, commit_b.tree)
        results = []
        for patch in tree_diff.deltas:
            status = _STATUS_MAP.get(patch.status, "modified")
            path = patch.new_file.path if patch.new_file.path else patch.old_file.path
            results.append({"path": path, "status": status})
        return results
```

- [ ] **Step 19: Run test to verify it passes**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: PASS (4 passed)

- [ ] **Step 20: Commit**

```bash
git add backend/app/versioning/git_adapter.py backend/tests/versioning/test_git_adapter.py
git commit -m "feat(versioning): diff two commits by path status"
```

- [ ] **Step 21: Write the failing test for `branch` and `branch_head`**

Append to `backend/tests/versioning/test_git_adapter.py`:

```python
def test_branch_creates_ref_pointing_at_given_commit():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n"})
    artifact = GitVersionedArtifact(repo_path)
    first_commit = artifact.commit(None, "user-1", "noop")

    artifact.branch("feature", "master")

    assert artifact.branch_head("feature") == first_commit
```

- [ ] **Step 22: Run test to verify it fails**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: FAIL with `AttributeError: 'GitVersionedArtifact' object has no attribute 'branch'`

- [ ] **Step 23: Write minimal implementation**

Add these two methods inside `GitVersionedArtifact`, after `diff`:

```python
    def branch(self, name: str, from_ref: str) -> None:
        commit = self._resolve_commit(from_ref)
        self.repo.branches.local.create(name, commit)

    def branch_head(self, name: str) -> str:
        branch_ref = self.repo.branches.local[name]
        return str(branch_ref.target)
```

- [ ] **Step 24: Run test to verify it passes**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: PASS (5 passed)

- [ ] **Step 25: Commit**

```bash
git add backend/app/versioning/git_adapter.py backend/tests/versioning/test_git_adapter.py
git commit -m "feat(versioning): create branches from an existing ref"
```

- [ ] **Step 26: Write the failing test for `checkout_branch`**

Append to `backend/tests/versioning/test_git_adapter.py`:

```python
def test_checkout_branch_switches_head_and_working_tree():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n"})
    artifact = GitVersionedArtifact(repo_path)
    artifact.branch("feature", "master")

    artifact.commit({"a.txt": "content a on master\n"}, "user-1", "edit on master")
    artifact.checkout_branch("feature")

    assert artifact.repo.head.shorthand == "feature"
    assert open(os.path.join(repo_path, "a.txt")).read() == "content a\n"
```

- [ ] **Step 27: Run test to verify it fails**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: FAIL with `AttributeError: 'GitVersionedArtifact' object has no attribute 'checkout_branch'`

- [ ] **Step 28: Write minimal implementation**

Add this method inside `GitVersionedArtifact`, after `branch_head`:

```python
    def checkout_branch(self, name: str) -> None:
        branch_ref = self.repo.branches.local[name]
        self.repo.set_head(branch_ref.name)
        self.repo.checkout(branch_ref, strategy=pygit2.GIT_CHECKOUT_FORCE)
```

- [ ] **Step 29: Run test to verify it passes**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: PASS (6 passed)

- [ ] **Step 30: Commit**

```bash
git add backend/app/versioning/git_adapter.py backend/tests/versioning/test_git_adapter.py
git commit -m "feat(versioning): checkout a branch into the working tree"
```

- [ ] **Step 31: Write the failing test for `get_content`**

Append to `backend/tests/versioning/test_git_adapter.py`:

```python
def test_get_content_returns_all_blobs_at_a_commit():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(
        repo_path, {"a.txt": "content a\n", "b.txt": "content b\n"}
    )
    artifact = GitVersionedArtifact(repo_path)
    commit_id = artifact.commit(None, "user-1", "noop")

    content = artifact.get_content(commit_id)

    assert content == {"a.txt": "content a\n", "b.txt": "content b\n"}
```

- [ ] **Step 32: Run test to verify it fails**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: FAIL with `AttributeError: 'GitVersionedArtifact' object has no attribute 'get_content'`

- [ ] **Step 33: Write minimal implementation**

Add this method inside `GitVersionedArtifact`, after `checkout_branch`:

```python
    def get_content(self, ref: str) -> dict:
        commit = self._resolve_commit(ref)
        result = {}

        def walk(tree, prefix=""):
            for entry in tree:
                full_path = prefix + entry.name
                obj = self.repo[entry.id]
                if isinstance(obj, pygit2.Tree):
                    walk(obj, full_path + "/")
                else:
                    result[full_path] = obj.data.decode("utf-8")

        walk(commit.tree)
        return result
```

- [ ] **Step 34: Run test to verify it passes**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: PASS (7 passed)

- [ ] **Step 35: Commit**

```bash
git add backend/app/versioning/git_adapter.py backend/tests/versioning/test_git_adapter.py
git commit -m "feat(versioning): read all blob contents at a commit"
```

- [ ] **Step 36: Write the failing test for a non-conflicting `merge`**

Append to `backend/tests/versioning/test_git_adapter.py`:

```python
def test_merge_without_conflicts_combines_both_branches_edits():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(
        repo_path, {"a.txt": "content a\n", "b.txt": "content b\n"}
    )
    artifact = GitVersionedArtifact(repo_path)
    artifact.branch("feature", "master")
    base_ref = artifact.branch_head("feature")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "content a edited on feature\n"}, "user-1", "edit a on feature")

    artifact.checkout_branch("master")
    artifact.commit({"b.txt": "content b edited on master\n"}, "user-1", "edit b on master")

    result = artifact.merge(base_ref, "master", "feature")

    assert result["merged"] is True
    assert result["conflicts"] == []
    merged_content = artifact.get_content("master")
    assert merged_content["a.txt"] == "content a edited on feature\n"
    assert merged_content["b.txt"] == "content b edited on master\n"
```

Note that `base_ref` is captured immediately after creating the `feature` branch, before either branch is edited, so it names the common ancestor commit rather than a ref that keeps moving as `master` advances.

- [ ] **Step 37: Run test to verify it fails**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: FAIL with `AttributeError: 'GitVersionedArtifact' object has no attribute 'merge'`

- [ ] **Step 38: Write minimal implementation**

Add this method inside `GitVersionedArtifact`, after `get_content`:

```python
    def merge(self, base_ref: str, ours_ref: str, theirs_ref: str) -> dict:
        base_commit = self._resolve_commit(base_ref)
        ours_commit = self._resolve_commit(ours_ref)
        theirs_commit = self._resolve_commit(theirs_ref)

        merge_index = self.repo.merge_trees(
            base_commit.tree, ours_commit.tree, theirs_commit.tree
        )

        merge_tree_id = merge_index.write_tree(self.repo)
        signature = pygit2.Signature("system", "system@local")
        merge_commit_id = self.repo.create_commit(
            None,
            signature,
            signature,
            f"merge {theirs_ref} into {ours_ref}",
            merge_tree_id,
            [ours_commit.id, theirs_commit.id],
        )
        ours_branch = self.repo.branches.local.get(ours_ref)
        if ours_branch is not None:
            ours_branch.set_target(merge_commit_id)
            # Move HEAD, the working directory, and the on-disk index to the
            # merge commit's tree. Without this, the working directory still
            # holds the pre-merge content, and the next commit() call's
            # index.add_all() re-stages that stale content, silently
            # reverting the merge.
            self.checkout_branch(ours_ref)
        return {"merged": True, "conflicts": []}
```

- [ ] **Step 39: Run test to verify it passes**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: PASS (8 passed)

- [ ] **Step 40: Commit**

```bash
git add backend/app/versioning/git_adapter.py backend/tests/versioning/test_git_adapter.py
git commit -m "feat(versioning): merge two branches without conflicts"
```

- [ ] **Step 41: Write the failing test for a conflicting `merge`**

Append to `backend/tests/versioning/test_git_adapter.py`:

```python
def test_merge_with_conflicting_edits_returns_single_conflict():
    repo_path = tempfile.mkdtemp()
    init_repo_from_files(repo_path, {"a.txt": "content a\n"})
    artifact = GitVersionedArtifact(repo_path)
    artifact.branch("feature", "master")
    base_ref = artifact.branch_head("feature")

    artifact.checkout_branch("feature")
    artifact.commit({"a.txt": "feature version of a\n"}, "user-1", "edit a on feature")

    artifact.checkout_branch("master")
    artifact.commit({"a.txt": "master version of a\n"}, "user-1", "edit a on master")

    result = artifact.merge(base_ref, "master", "feature")

    assert result["merged"] is False
    assert len(result["conflicts"]) == 1
    conflict = result["conflicts"][0]
    assert conflict["path"] == "a.txt"
    assert conflict["ours"] == "master version of a\n"
    assert conflict["theirs"] == "feature version of a\n"
    assert conflict["base"] == "content a\n"
```

- [ ] **Step 42: Run test to verify it fails**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: FAIL with `_pygit2.GitError: cannot create a tree from a not fully merged index.` (the current `merge` implementation calls `write_tree` unconditionally, and libgit2 refuses to build a tree from an index that still has unresolved conflict entries)

- [ ] **Step 43: Write minimal implementation**

Replace the body of `merge` inside `GitVersionedArtifact` in `backend/app/versioning/git_adapter.py` with a version that checks for conflicts before writing the tree:

```python
    def merge(self, base_ref: str, ours_ref: str, theirs_ref: str) -> dict:
        base_commit = self._resolve_commit(base_ref)
        ours_commit = self._resolve_commit(ours_ref)
        theirs_commit = self._resolve_commit(theirs_ref)

        merge_index = self.repo.merge_trees(
            base_commit.tree, ours_commit.tree, theirs_commit.tree
        )

        if merge_index.conflicts is not None:
            conflicts = []
            for ancestor, ours, theirs in merge_index.conflicts:
                path = None
                ours_text = None
                theirs_text = None
                base_text = None
                if ours is not None:
                    path = ours.path
                    ours_text = self.repo[ours.id].data.decode("utf-8")
                if theirs is not None:
                    path = path or theirs.path
                    theirs_text = self.repo[theirs.id].data.decode("utf-8")
                if ancestor is not None:
                    path = path or ancestor.path
                    base_text = self.repo[ancestor.id].data.decode("utf-8")
                conflicts.append(
                    {
                        "path": path,
                        "ours": ours_text,
                        "theirs": theirs_text,
                        "base": base_text,
                    }
                )
            return {"merged": False, "conflicts": conflicts}

        merge_tree_id = merge_index.write_tree(self.repo)
        signature = pygit2.Signature("system", "system@local")
        merge_commit_id = self.repo.create_commit(
            None,
            signature,
            signature,
            f"merge {theirs_ref} into {ours_ref}",
            merge_tree_id,
            [ours_commit.id, theirs_commit.id],
        )
        ours_branch = self.repo.branches.local.get(ours_ref)
        if ours_branch is not None:
            ours_branch.set_target(merge_commit_id)
            # Move HEAD, the working directory, and the on-disk index to the
            # merge commit's tree. Without this, the working directory still
            # holds the pre-merge content, and the next commit() call's
            # index.add_all() re-stages that stale content, silently
            # reverting the merge.
            self.checkout_branch(ours_ref)
        return {"merged": True, "conflicts": []}
```

- [ ] **Step 44: Run test to verify it passes**

Run: `cd backend && pytest tests/versioning/test_git_adapter.py -v`
Expected: PASS (9 passed)

- [ ] **Step 45: Commit**

```bash
git add backend/app/versioning/git_adapter.py backend/tests/versioning/test_git_adapter.py
git commit -m "feat(versioning): report conflicts when a merge cannot be resolved automatically"
```

### Task 9: Tree-Sitter Structural Diff for Code

**Files:**
- Create: backend/app/versioning/code_diff.py
- Test: backend/tests/versioning/test_code_diff.py

**Interfaces:**
- Consumes: none from earlier tasks. This module depends only on the third-party `tree_sitter` and `tree_sitter_python` libraries and the existing `backend/app` package layout created by the project skeleton task.
- Produces: `structural_diff(old_code: str, new_code: str, language: str) -> list`, where each entry is a dict shaped as `{"node_type": str, "name": str, "status": str}` with `status` one of `added`, `removed`, `modified`.

- [ ] **Step 1: Write the failing test for detecting an added function**

Create `backend/tests/versioning/test_code_diff.py`:

```python
from app.versioning.code_diff import structural_diff


def test_structural_diff_detects_added_function():
    old_code = "def foo():\n    return 1\n"
    new_code = "def foo():\n    return 1\n\n\ndef baz():\n    return 3\n"

    result = structural_diff(old_code, new_code, "python")

    assert result == [
        {"node_type": "function_definition", "name": "baz", "status": "added"}
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/versioning/test_code_diff.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.versioning.code_diff'`

- [ ] **Step 3: Write minimal implementation**

Add `tree-sitter==0.26.0` and `tree-sitter-python==0.25.0` to `backend/requirements.txt` and install with `pip install -r backend/requirements.txt`. Create `backend/app/versioning/code_diff.py`:

```python
import tree_sitter_python
from tree_sitter import Language, Node, Parser

_LANGUAGES = {
    "python": Language(tree_sitter_python.language()),
}

_DEFINITION_NODE_TYPES = ("function_definition", "class_definition")


def _get_parser(language: str) -> Parser:
    return Parser(_LANGUAGES[language])


def _extract_definitions(source: str, language: str) -> dict:
    parser = _get_parser(language)
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)
    definitions = {}

    # Only scan direct children of the module (one level, no recursion) so
    # this stays scoped to genuinely top-level functions/classes. Recursing
    # into matched or unmatched nodes would also pick up methods nested
    # inside classes, and since those are keyed by name alone, two classes
    # that both define e.g. __init__ would collide in this dict and one
    # change would silently overwrite or shadow the other.
    for child in tree.root_node.children:
        if child.type in _DEFINITION_NODE_TYPES:
            name_node = child.child_by_field_name("name")
            if name_node is not None:
                name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
                text = source_bytes[child.start_byte:child.end_byte].decode("utf-8")
                definitions[name] = {"node_type": child.type, "text": text}

    return definitions


def structural_diff(old_code: str, new_code: str, language: str) -> list:
    old_defs = _extract_definitions(old_code, language)
    new_defs = _extract_definitions(new_code, language)

    results = []
    for name, new_def in new_defs.items():
        if name not in old_defs:
            results.append(
                {"node_type": new_def["node_type"], "name": name, "status": "added"}
            )
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/versioning/test_code_diff.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/versioning/code_diff.py backend/tests/versioning/test_code_diff.py
git commit -m "feat(versioning): detect added top-level definitions in structural diff"
```

- [ ] **Step 6: Write the failing test for detecting a removed function**

Append to `backend/tests/versioning/test_code_diff.py`:

```python
def test_structural_diff_detects_removed_function():
    old_code = "def foo():\n    return 1\n\n\ndef bar():\n    return 2\n"
    new_code = "def foo():\n    return 1\n"

    result = structural_diff(old_code, new_code, "python")

    assert result == [
        {"node_type": "function_definition", "name": "bar", "status": "removed"}
    ]
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd backend && pytest tests/versioning/test_code_diff.py -v`
Expected: FAIL with `AssertionError: assert [] == [{'node_type': 'function_definition', 'name': 'bar', 'status': 'removed'}]`

- [ ] **Step 8: Write minimal implementation**

Replace the body of `structural_diff` in `backend/app/versioning/code_diff.py` with:

```python
def structural_diff(old_code: str, new_code: str, language: str) -> list:
    old_defs = _extract_definitions(old_code, language)
    new_defs = _extract_definitions(new_code, language)

    results = []
    for name, new_def in new_defs.items():
        if name not in old_defs:
            results.append(
                {"node_type": new_def["node_type"], "name": name, "status": "added"}
            )

    for name, old_def in old_defs.items():
        if name not in new_defs:
            results.append(
                {"node_type": old_def["node_type"], "name": name, "status": "removed"}
            )

    return results
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd backend && pytest tests/versioning/test_code_diff.py -v`
Expected: PASS (2 passed)

- [ ] **Step 10: Commit**

```bash
git add backend/app/versioning/code_diff.py backend/tests/versioning/test_code_diff.py
git commit -m "feat(versioning): detect removed top-level definitions in structural diff"
```

- [ ] **Step 11: Write the failing test for the combined added, removed, and modified scenario**

Append to `backend/tests/versioning/test_code_diff.py`:

```python
def test_structural_diff_detects_modified_removed_and_added_functions():
    old_code = "def foo():\n    return 1\n\n\ndef bar():\n    return 2\n"
    new_code = "def foo():\n    return 999\n\n\ndef baz():\n    return 3\n"

    result = structural_diff(old_code, new_code, "python")
    result_by_name = {entry["name"]: entry for entry in result}

    assert len(result) == 3
    assert result_by_name["foo"] == {
        "node_type": "function_definition",
        "name": "foo",
        "status": "modified",
    }
    assert result_by_name["bar"] == {
        "node_type": "function_definition",
        "name": "bar",
        "status": "removed",
    }
    assert result_by_name["baz"] == {
        "node_type": "function_definition",
        "name": "baz",
        "status": "added",
    }
```

- [ ] **Step 12: Run test to verify it fails**

Run: `cd backend && pytest tests/versioning/test_code_diff.py -v`
Expected: FAIL with `AssertionError: assert 2 == 3` (`foo` is present in both `old_defs` and `new_defs` with different source text, so it is silently dropped instead of being reported as modified)

- [ ] **Step 13: Write minimal implementation**

Replace the body of `structural_diff` in `backend/app/versioning/code_diff.py` with:

```python
def structural_diff(old_code: str, new_code: str, language: str) -> list:
    old_defs = _extract_definitions(old_code, language)
    new_defs = _extract_definitions(new_code, language)

    results = []
    for name, new_def in new_defs.items():
        if name not in old_defs:
            results.append(
                {"node_type": new_def["node_type"], "name": name, "status": "added"}
            )
        elif old_defs[name]["text"] != new_def["text"]:
            results.append(
                {"node_type": new_def["node_type"], "name": name, "status": "modified"}
            )

    for name, old_def in old_defs.items():
        if name not in new_defs:
            results.append(
                {"node_type": old_def["node_type"], "name": name, "status": "removed"}
            )

    return results
```

- [ ] **Step 14: Run test to verify it passes**

Run: `cd backend && pytest tests/versioning/test_code_diff.py -v`
Expected: PASS (3 passed)

- [ ] **Step 15: Commit**

```bash
git add backend/app/versioning/code_diff.py backend/tests/versioning/test_code_diff.py
git commit -m "feat(versioning): detect modified top-level definitions in structural diff"
```

### Task 10: Markdown Parser and Shared ParsedArtifact Type

**Files:**
- Create: backend/app/ingestion/__init__.py
- Create: backend/app/ingestion/base.py
- Create: backend/app/ingestion/markdown_parser.py
- Create: backend/tests/fixtures/sample.md
- Test: backend/tests/ingestion/test_markdown_parser.py

**Interfaces:**
- Consumes: none. This is the first ingestion task and it defines the shared type every other ingestion task depends on.
- Produces:
  - `ParsedArtifact(artifact_type: str, name: str, content: Union[str, dict])` — dataclass defined in `backend/app/ingestion/base.py`, imported by every later ingestion task as `from app.ingestion.base import ParsedArtifact`.
  - `parse_markdown(file_bytes: bytes, filename: str) -> ParsedArtifact` — defined in `backend/app/ingestion/markdown_parser.py`.

- [ ] **Step 1: Create the markdown fixture file**

Create the fixtures directory and a small known-content markdown file that the test will parse.

```bash
mkdir -p backend/tests/fixtures
cat > backend/tests/fixtures/sample.md << 'EOF'
# Sample Notes

This is a sample markdown fixture used to test the markdown parser.
EOF
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/ingestion/test_markdown_parser.py
from pathlib import Path

from app.ingestion.base import ParsedArtifact
from app.ingestion.markdown_parser import parse_markdown

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_markdown_returns_parsed_artifact():
    fixture_path = FIXTURES_DIR / "sample.md"
    file_bytes = fixture_path.read_bytes()
    expected_text = fixture_path.read_text(encoding="utf-8")

    result = parse_markdown(file_bytes, "sample.md")

    assert isinstance(result, ParsedArtifact)
    assert result.artifact_type == "doc"
    assert result.name == "sample.md"
    assert result.content == expected_text
```

- [ ] **Step 3: Run the test and confirm it fails**

Run: `cd backend && python -m pytest tests/ingestion/test_markdown_parser.py -v`

Expected failure: `ModuleNotFoundError: No module named 'app.ingestion'` (neither `base.py` nor `markdown_parser.py` exist yet).

- [ ] **Step 4: Write the minimal implementation**

```python
# backend/app/ingestion/__init__.py
```

```python
# backend/app/ingestion/base.py
from dataclasses import dataclass
from typing import Union


@dataclass
class ParsedArtifact:
    artifact_type: str
    name: str
    content: Union[str, dict]
```

```python
# backend/app/ingestion/markdown_parser.py
from app.ingestion.base import ParsedArtifact


def parse_markdown(file_bytes: bytes, filename: str) -> ParsedArtifact:
    text = file_bytes.decode("utf-8")
    return ParsedArtifact(artifact_type="doc", name=filename, content=text)
```

- [ ] **Step 5: Run the test again and confirm it passes**

Run: `cd backend && python -m pytest tests/ingestion/test_markdown_parser.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/ingestion/__init__.py backend/app/ingestion/base.py backend/app/ingestion/markdown_parser.py backend/tests/fixtures/sample.md backend/tests/ingestion/test_markdown_parser.py
git commit -m "feat(ingestion): add markdown parser and shared ParsedArtifact type"
```

### Task 11: ChatGPT Export Parser

**Files:**
- Create: backend/app/ingestion/chatgpt_parser.py
- Create: backend/tests/fixtures/chatgpt_conversations.json
- Test: backend/tests/ingestion/test_chatgpt_parser.py

**Interfaces:**
- Consumes: `ParsedArtifact(artifact_type: str, name: str, content: Union[str, dict])` from `backend/app/ingestion/base.py` (Task 10).
- Produces: `parse_chatgpt_export(json_bytes: bytes) -> List[ParsedArtifact]` — defined in `backend/app/ingestion/chatgpt_parser.py`. Each returned artifact has `content` equal to a JSON string encoding a list of `{"role": str, "text": str, "ts": float}` objects, the same shape expected by the tokenizer used for chat diffing and chunking.

- [ ] **Step 1: Create the ChatGPT export fixture**

The fixture contains one conversation with a linear chain of three messages plus one discarded alternate branch. Node `n1` has two children, `alt2` and `n2`; `alt2` is listed first and is the earlier, abandoned regeneration, while `n2` is listed last and continues the current path.

```bash
mkdir -p backend/tests/fixtures
cat > backend/tests/fixtures/chatgpt_conversations.json << 'EOF'
[
  {
    "title": "Reversing a string",
    "mapping": {
      "root": {
        "id": "root",
        "message": null,
        "parent": null,
        "children": ["n1"]
      },
      "n1": {
        "id": "n1",
        "message": {
          "author": {"role": "user"},
          "content": {"parts": ["How do I reverse a string in Python?"]},
          "create_time": 1000.0
        },
        "parent": "root",
        "children": ["alt2", "n2"]
      },
      "alt2": {
        "id": "alt2",
        "message": {
          "author": {"role": "assistant"},
          "content": {"parts": ["Use reversed(s)."]},
          "create_time": 1001.0
        },
        "parent": "n1",
        "children": []
      },
      "n2": {
        "id": "n2",
        "message": {
          "author": {"role": "assistant"},
          "content": {"parts": ["You can use s[::-1] to reverse a string."]},
          "create_time": 1002.0
        },
        "parent": "n1",
        "children": ["n3"]
      },
      "n3": {
        "id": "n3",
        "message": {
          "author": {"role": "user"},
          "content": {"parts": ["Great, thanks!"]},
          "create_time": 1003.0
        },
        "parent": "n2",
        "children": []
      }
    }
  }
]
EOF
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/ingestion/test_chatgpt_parser.py
import json
from pathlib import Path

from app.ingestion.base import ParsedArtifact
from app.ingestion.chatgpt_parser import parse_chatgpt_export

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_chatgpt_export_follows_current_branch_only():
    fixture_path = FIXTURES_DIR / "chatgpt_conversations.json"
    json_bytes = fixture_path.read_bytes()

    artifacts = parse_chatgpt_export(json_bytes)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert isinstance(artifact, ParsedArtifact)
    assert artifact.artifact_type == "chat"
    assert artifact.name == "Reversing a string"

    messages = json.loads(artifact.content)
    assert messages == [
        {"role": "user", "text": "How do I reverse a string in Python?", "ts": 1000.0},
        {"role": "assistant", "text": "You can use s[::-1] to reverse a string.", "ts": 1002.0},
        {"role": "user", "text": "Great, thanks!", "ts": 1003.0},
    ]
    texts = [message["text"] for message in messages]
    assert "Use reversed(s)." not in texts
```

- [ ] **Step 3: Run the test and confirm it fails**

Run: `cd backend && python -m pytest tests/ingestion/test_chatgpt_parser.py -v`

Expected failure: `ModuleNotFoundError: No module named 'app.ingestion.chatgpt_parser'`

- [ ] **Step 4: Write the minimal implementation**

```python
# backend/app/ingestion/chatgpt_parser.py
import json
from typing import List, Optional

from app.ingestion.base import ParsedArtifact


def _find_root_id(mapping: dict) -> Optional[str]:
    for node_id, node in mapping.items():
        if node.get("parent") is None:
            return node_id
    return None


def _walk_current_path(mapping: dict) -> list:
    current_id = _find_root_id(mapping)
    messages = []

    while current_id is not None:
        node = mapping[current_id]
        message = node.get("message")
        if message is not None:
            role = message["author"]["role"]
            text = "".join(message["content"]["parts"])
            messages.append(
                {
                    "role": role,
                    "text": text,
                    "ts": message["create_time"],
                }
            )
        children = node.get("children") or []
        current_id = children[-1] if children else None

    messages.sort(key=lambda entry: entry["ts"])
    return messages


def parse_chatgpt_export(json_bytes: bytes) -> List[ParsedArtifact]:
    conversations = json.loads(json_bytes.decode("utf-8"))
    artifacts = []

    for conversation in conversations:
        messages = _walk_current_path(conversation["mapping"])
        content = json.dumps(messages)
        artifacts.append(
            ParsedArtifact(
                artifact_type="chat",
                name=conversation["title"],
                content=content,
            )
        )

    return artifacts
```

- [ ] **Step 5: Run the test again and confirm it passes**

Run: `cd backend && python -m pytest tests/ingestion/test_chatgpt_parser.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/ingestion/chatgpt_parser.py backend/tests/fixtures/chatgpt_conversations.json backend/tests/ingestion/test_chatgpt_parser.py
git commit -m "feat(ingestion): add ChatGPT export parser with branch flattening"
```

### Task 12: Claude Export Parser

**Files:**
- Create: backend/app/ingestion/claude_parser.py
- Create: backend/tests/fixtures/claude_conversations.json
- Test: backend/tests/ingestion/test_claude_parser.py

**Interfaces:**
- Consumes: `ParsedArtifact(artifact_type: str, name: str, content: Union[str, dict])` from `backend/app/ingestion/base.py` (Task 10).
- Produces: `parse_claude_export(json_bytes: bytes) -> List[ParsedArtifact]` — defined in `backend/app/ingestion/claude_parser.py`. Each returned artifact has `content` equal to a JSON string encoding a list of `{"role": str, "text": str, "ts": str}` objects, the same normalized shape produced by `parse_chatgpt_export`.

- [ ] **Step 1: Create the Claude export fixture**

The fixture is a flat, already-ordered list of messages with no tree structure, alternating `human` and `assistant` senders.

```bash
mkdir -p backend/tests/fixtures
cat > backend/tests/fixtures/claude_conversations.json << 'EOF'
[
  {
    "name": "Debugging a Python script",
    "chat_messages": [
      {
        "sender": "human",
        "text": "Why does my script raise a KeyError?",
        "created_at": "2026-01-01T10:00:00Z"
      },
      {
        "sender": "assistant",
        "text": "A KeyError means the dictionary key you accessed does not exist.",
        "created_at": "2026-01-01T10:00:05Z"
      },
      {
        "sender": "human",
        "text": "Got it, thanks!",
        "created_at": "2026-01-01T10:00:12Z"
      }
    ]
  }
]
EOF
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/ingestion/test_claude_parser.py
import json
from pathlib import Path

from app.ingestion.base import ParsedArtifact
from app.ingestion.claude_parser import parse_claude_export

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_claude_export_maps_roles_and_preserves_order():
    fixture_path = FIXTURES_DIR / "claude_conversations.json"
    json_bytes = fixture_path.read_bytes()

    artifacts = parse_claude_export(json_bytes)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert isinstance(artifact, ParsedArtifact)
    assert artifact.artifact_type == "chat"
    assert artifact.name == "Debugging a Python script"

    messages = json.loads(artifact.content)
    assert messages == [
        {
            "role": "user",
            "text": "Why does my script raise a KeyError?",
            "ts": "2026-01-01T10:00:00Z",
        },
        {
            "role": "assistant",
            "text": "A KeyError means the dictionary key you accessed does not exist.",
            "ts": "2026-01-01T10:00:05Z",
        },
        {
            "role": "user",
            "text": "Got it, thanks!",
            "ts": "2026-01-01T10:00:12Z",
        },
    ]
```

- [ ] **Step 3: Run the test and confirm it fails**

Run: `cd backend && python -m pytest tests/ingestion/test_claude_parser.py -v`

Expected failure: `ModuleNotFoundError: No module named 'app.ingestion.claude_parser'`

- [ ] **Step 4: Write the minimal implementation**

```python
# backend/app/ingestion/claude_parser.py
import json
from typing import List

from app.ingestion.base import ParsedArtifact

_SENDER_TO_ROLE = {
    "human": "user",
    "assistant": "assistant",
}


def parse_claude_export(json_bytes: bytes) -> List[ParsedArtifact]:
    conversations = json.loads(json_bytes.decode("utf-8"))
    artifacts = []

    for conversation in conversations:
        messages = []
        for chat_message in conversation["chat_messages"]:
            role = _SENDER_TO_ROLE[chat_message["sender"]]
            messages.append(
                {
                    "role": role,
                    "text": chat_message["text"],
                    "ts": chat_message["created_at"],
                }
            )
        content = json.dumps(messages)
        artifacts.append(
            ParsedArtifact(
                artifact_type="chat",
                name=conversation["name"],
                content=content,
            )
        )

    return artifacts
```

- [ ] **Step 5: Run the test again and confirm it passes**

Run: `cd backend && python -m pytest tests/ingestion/test_claude_parser.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/ingestion/claude_parser.py backend/tests/fixtures/claude_conversations.json backend/tests/ingestion/test_claude_parser.py
git commit -m "feat(ingestion): add Claude export parser"
```

### Task 13: PDF Parser

**Files:**
- Create: backend/app/ingestion/pdf_parser.py
- Create: backend/tests/fixtures/generate_sample_pdf.py
- Create: backend/tests/fixtures/sample.pdf
- Modify: backend/requirements.txt
- Test: backend/tests/ingestion/test_pdf_parser.py

**Interfaces:**
- Consumes: `ParsedArtifact(artifact_type: str, name: str, content: Union[str, dict])` from `backend/app/ingestion/base.py` (Task 10).
- Produces: `parse_pdf(file_bytes: bytes, filename: str) -> ParsedArtifact` — defined in `backend/app/ingestion/pdf_parser.py`. The returned artifact has `content` equal to a JSON string encoding a list of `{"page": int, "text": str}` objects, one per page, with `page` numbered starting at 1.

This task requires a real, binary PDF fixture with known text content, because `pdfplumber` must extract text from an actual PDF page stream, not a mock. The fixture must be generated, not hand-authored, since PDF is a binary format. The exact expected content after extraction is two pages, page 1 containing the single line `Page one content.` and page 2 containing the single line `Page two content.`.

- [ ] **Step 1: Generate the PDF fixture with known text content**

Install `reportlab` as a one-time, local tool for generating the fixture. `reportlab` is not a runtime dependency of `parse_pdf` and is not added to `backend/requirements.txt`; it is only used to produce the committed binary file.

```bash
pip install reportlab
```

```python
# backend/tests/fixtures/generate_sample_pdf.py
"""One-time generator for backend/tests/fixtures/sample.pdf.

Produces a two-page PDF where page 1 contains the single line
"Page one content." and page 2 contains the single line
"Page two content.". Re-run this script only if the fixture needs to be
regenerated; the resulting sample.pdf is committed to the repository.
"""
from reportlab.pdfgen import canvas

PDF_PATH = "backend/tests/fixtures/sample.pdf"


def generate() -> None:
    pdf_canvas = canvas.Canvas(PDF_PATH, pagesize=(612, 792))

    pdf_canvas.drawString(72, 700, "Page one content.")
    pdf_canvas.showPage()

    pdf_canvas.drawString(72, 700, "Page two content.")
    pdf_canvas.showPage()

    pdf_canvas.save()


if __name__ == "__main__":
    generate()
```

```bash
python backend/tests/fixtures/generate_sample_pdf.py
ls -la backend/tests/fixtures/sample.pdf
```

Expected: `sample.pdf` now exists as a non-empty binary file under `backend/tests/fixtures/`.

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/ingestion/test_pdf_parser.py
import json
from pathlib import Path

from app.ingestion.base import ParsedArtifact
from app.ingestion.pdf_parser import parse_pdf

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_pdf_extracts_text_per_page():
    fixture_path = FIXTURES_DIR / "sample.pdf"
    file_bytes = fixture_path.read_bytes()

    result = parse_pdf(file_bytes, "sample.pdf")

    assert isinstance(result, ParsedArtifact)
    assert result.artifact_type == "pdf"
    assert result.name == "sample.pdf"

    pages = json.loads(result.content)
    assert len(pages) == 2
    assert pages[0]["page"] == 1
    assert pages[0]["text"].strip() == "Page one content."
    assert pages[1]["page"] == 2
    assert pages[1]["text"].strip() == "Page two content."
```

- [ ] **Step 3: Run the test and confirm it fails**

Run: `cd backend && python -m pytest tests/ingestion/test_pdf_parser.py -v`

Expected failure: `ModuleNotFoundError: No module named 'app.ingestion.pdf_parser'`

- [ ] **Step 4: Add the pdfplumber dependency and write the minimal implementation**

```
# backend/requirements.txt (append this line)
pdfplumber
```

```bash
pip install pdfplumber
```

```python
# backend/app/ingestion/pdf_parser.py
import io
import json

import pdfplumber

from app.ingestion.base import ParsedArtifact


def parse_pdf(file_bytes: bytes, filename: str) -> ParsedArtifact:
    pages = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"page": page_number, "text": text})

    content = json.dumps(pages)
    return ParsedArtifact(artifact_type="pdf", name=filename, content=content)
```

- [ ] **Step 5: Run the test again and confirm it passes**

Run: `cd backend && python -m pytest tests/ingestion/test_pdf_parser.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/ingestion/pdf_parser.py backend/tests/fixtures/generate_sample_pdf.py backend/tests/fixtures/sample.pdf backend/tests/ingestion/test_pdf_parser.py backend/requirements.txt
git commit -m "feat(ingestion): add PDF parser using pdfplumber"
```

### Task 14: Codebase Ingestion from Zip or Existing Git Repository

**Files:**
- Create: backend/app/ingestion/codebase_parser.py
- Test: backend/tests/ingestion/test_codebase_parser.py
- Test: backend/tests/ingestion/test_codebase_git_parser.py

**Interfaces:**
- Consumes: `ParsedArtifact(artifact_type, name, content)` from `backend/app/ingestion/base.py`, where `content` is typed as `Union[str, Dict[str, str]]`; `init_repo_from_files(repo_path, files)` and `clone_repo(source_path_or_url, dest_path)` from `backend/app/versioning/git_adapter.py`.
- Produces: `parse_codebase_zip(zip_bytes: bytes) -> ParsedArtifact` and `parse_codebase_git(repo_path_or_url: str, dest_path: str) -> ParsedArtifact`, both in `backend/app/ingestion/codebase_parser.py`.

- [ ] **Step 1: Write a failing test for zip extraction with binary skipping**

Create `backend/tests/ingestion/test_codebase_parser.py` with a test that builds an in memory zip fixture containing two text files and one file with invalid utf-8 bytes, then asserts that `parse_codebase_zip` returns only the two text files with correct contents.

```python
import io
import zipfile

from app.ingestion.codebase_parser import parse_codebase_zip


def _build_zip_bytes(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for filename, raw_bytes in entries.items():
            archive.writestr(filename, raw_bytes)
    return buffer.getvalue()


def test_parse_codebase_zip_extracts_text_and_skips_binary():
    zip_bytes = _build_zip_bytes(
        {
            "main.py": b"print('hello world')\n",
            "README.md": b"# Sample Project\n",
            "data.bin": b"\xff\xfe\x00\x01binary-garbage\x80\x81",
        }
    )

    artifact = parse_codebase_zip(zip_bytes)

    assert artifact.artifact_type == "codebase"
    assert artifact.name == "codebase"
    assert artifact.content == {
        "main.py": "print('hello world')\n",
        "README.md": "# Sample Project\n",
    }
    assert "data.bin" not in artifact.content
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```
cd backend && python3 -m pytest tests/ingestion/test_codebase_parser.py -q
```

Expected failure output:

```
ImportError while importing test module '.../tests/ingestion/test_codebase_parser.py'.
...
E   ModuleNotFoundError: No module named 'app.ingestion.codebase_parser'
```

- [ ] **Step 3: Implement minimal parse_codebase_zip**

Create `backend/app/ingestion/codebase_parser.py` with a first implementation that opens the archive from an in memory buffer, decodes each entry as utf-8, skips entries that raise `UnicodeDecodeError`, and returns a `ParsedArtifact` with a fixed fallback name.

```python
import io
import zipfile
from typing import Dict

from app.ingestion.base import ParsedArtifact


def parse_codebase_zip(zip_bytes: bytes) -> ParsedArtifact:
    buffer = io.BytesIO(zip_bytes)
    files: Dict[str, str] = {}
    with zipfile.ZipFile(buffer) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            raw_bytes = archive.read(entry.filename)
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                continue
            files[entry.filename] = text
    return ParsedArtifact(artifact_type="codebase", name="codebase", content=files)
```

- [ ] **Step 4: Run the test and confirm it passes**

Run:

```
cd backend && python3 -m pytest tests/ingestion/test_codebase_parser.py -q
```

Expected output:

```
1 passed
```

- [ ] **Step 5: Commit the initial zip parser**

```
git add backend/app/ingestion/codebase_parser.py backend/tests/ingestion/test_codebase_parser.py
git commit -m "Add parse_codebase_zip with utf-8 decoding and binary file skipping"
```

- [ ] **Step 6: Write a failing test for top level directory name derivation**

Append a second test to `backend/tests/ingestion/test_codebase_parser.py` that builds a zip where every entry shares a single top level directory, and asserts the artifact name is derived from that directory instead of the fallback.

```python
def test_parse_codebase_zip_derives_name_from_top_level_directory():
    zip_bytes = _build_zip_bytes(
        {
            "sample_repo/main.py": b"print('hi')\n",
            "sample_repo/lib/util.py": b"def util():\n    return 1\n",
        }
    )

    artifact = parse_codebase_zip(zip_bytes)

    assert artifact.name == "sample_repo"
    assert artifact.content == {
        "sample_repo/main.py": "print('hi')\n",
        "sample_repo/lib/util.py": "def util():\n    return 1\n",
    }
```

- [ ] **Step 7: Run the test and confirm it fails**

Run:

```
cd backend && python3 -m pytest tests/ingestion/test_codebase_parser.py -q
```

Expected failure output:

```
>       assert artifact.name == "sample_repo"
E       AssertionError: assert 'codebase' == 'sample_repo'
E         
E         - sample_repo
E         + codebase
```

- [ ] **Step 8: Implement top level directory name derivation**

Update `backend/app/ingestion/codebase_parser.py` to add a helper that inspects every archive path, collects the first path segment when a path has more than one segment, and returns that segment as the name only if every entry shares exactly one such segment, otherwise falling back to the literal name `codebase`.

```python
import io
import zipfile
from typing import Dict, Iterable

from app.ingestion.base import ParsedArtifact


def _derive_top_level_name(paths: Iterable[str], fallback: str = "codebase") -> str:
    top_levels = set()
    for path in paths:
        normalized = path.replace("\\", "/")
        parts = normalized.split("/")
        if len(parts) > 1 and parts[0]:
            top_levels.add(parts[0])
    if len(top_levels) == 1:
        return top_levels.pop()
    return fallback


def parse_codebase_zip(zip_bytes: bytes) -> ParsedArtifact:
    buffer = io.BytesIO(zip_bytes)
    files: Dict[str, str] = {}
    with zipfile.ZipFile(buffer) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            raw_bytes = archive.read(entry.filename)
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                continue
            files[entry.filename] = text
        name = _derive_top_level_name(archive.namelist())
    return ParsedArtifact(artifact_type="codebase", name=name, content=files)
```

- [ ] **Step 9: Run the test and confirm both tests pass**

Run:

```
cd backend && python3 -m pytest tests/ingestion/test_codebase_parser.py -q
```

Expected output:

```
2 passed
```

- [ ] **Step 10: Commit the name derivation logic**

```
git add backend/app/ingestion/codebase_parser.py backend/tests/ingestion/test_codebase_parser.py
git commit -m "Derive codebase zip artifact name from shared top level directory"
```

- [ ] **Step 11: Write a failing test for git based ingestion**

Create `backend/tests/ingestion/test_codebase_git_parser.py` with a fixture that builds a temporary local git repository using subprocess calls to the `git` binary, commits one tracked text file, then asserts `parse_codebase_git` clones it into `dest_path` and returns the tracked file content.

```python
import subprocess

from app.ingestion.codebase_parser import parse_codebase_git


def _run_git(args, cwd):
    subprocess.run(
        ["git"] + args,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _make_source_repo(tmp_path):
    source_path = tmp_path / "source_repo"
    source_path.mkdir()
    _run_git(["init"], cwd=source_path)
    _run_git(["config", "user.email", "test@example.com"], cwd=source_path)
    _run_git(["config", "user.name", "Test User"], cwd=source_path)
    (source_path / "app.py").write_text("def add(a, b):\n    return a + b\n")
    _run_git(["add", "app.py"], cwd=source_path)
    _run_git(["commit", "-m", "initial commit"], cwd=source_path)
    return source_path


def test_parse_codebase_git_clones_and_reads_tracked_files(tmp_path):
    source_path = _make_source_repo(tmp_path)
    dest_path = tmp_path / "cloned_repo"

    artifact = parse_codebase_git(str(source_path), str(dest_path))

    assert artifact.artifact_type == "codebase"
    assert artifact.name == "cloned_repo"
    assert artifact.content == {"app.py": "def add(a, b):\n    return a + b\n"}
    assert (dest_path / ".git").is_dir()
```

- [ ] **Step 12: Run the test and confirm it fails**

Run:

```
cd backend && python3 -m pytest tests/ingestion/test_codebase_git_parser.py -q
```

Expected failure output:

```
ImportError while importing test module '.../tests/ingestion/test_codebase_git_parser.py'.
...
E   ImportError: cannot import name 'parse_codebase_git' from 'app.ingestion.codebase_parser'
```

- [ ] **Step 13: Implement parse_codebase_git**

Update `backend/app/ingestion/codebase_parser.py` to add `parse_codebase_git`, which calls `clone_repo(repo_path_or_url, dest_path)`, then walks the working tree at `dest_path` skipping the `.git` directory, reading every file as utf-8 text and skipping entries that raise `UnicodeDecodeError`, and returns a `ParsedArtifact` whose name is the base name of `dest_path`.

```python
import io
import os
import zipfile
from typing import Dict, Iterable

from app.ingestion.base import ParsedArtifact
from app.versioning.git_adapter import clone_repo


def _derive_top_level_name(paths: Iterable[str], fallback: str = "codebase") -> str:
    top_levels = set()
    for path in paths:
        normalized = path.replace("\\", "/")
        parts = normalized.split("/")
        if len(parts) > 1 and parts[0]:
            top_levels.add(parts[0])
    if len(top_levels) == 1:
        return top_levels.pop()
    return fallback


def parse_codebase_zip(zip_bytes: bytes) -> ParsedArtifact:
    buffer = io.BytesIO(zip_bytes)
    files: Dict[str, str] = {}
    with zipfile.ZipFile(buffer) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            raw_bytes = archive.read(entry.filename)
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                continue
            files[entry.filename] = text
        name = _derive_top_level_name(archive.namelist())
    return ParsedArtifact(artifact_type="codebase", name=name, content=files)


def parse_codebase_git(repo_path_or_url: str, dest_path: str) -> ParsedArtifact:
    clone_repo(repo_path_or_url, dest_path)
    # Full history is preserved separately because dest_path is the git
    # repository later opened by GitVersionedArtifact; this ParsedArtifact
    # content field is only a snapshot used for chunking and retrieval.
    files: Dict[str, str] = {}
    for root, dirs, filenames in os.walk(dest_path):
        if ".git" in dirs:
            dirs.remove(".git")
        for filename in filenames:
            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, dest_path).replace(os.sep, "/")
            with open(full_path, "rb") as handle:
                raw_bytes = handle.read()
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                continue
            files[relative_path] = text
    name = os.path.basename(os.path.normpath(dest_path))
    return ParsedArtifact(artifact_type="codebase", name=name, content=files)
```

- [ ] **Step 14: Run the test and confirm it passes**

Run:

```
cd backend && python3 -m pytest tests/ingestion/test_codebase_git_parser.py tests/ingestion/test_codebase_parser.py -q
```

Expected output:

```
3 passed
```

- [ ] **Step 15: Commit the git based codebase parser**

```
git add backend/app/ingestion/codebase_parser.py backend/tests/ingestion/test_codebase_git_parser.py
git commit -m "Add parse_codebase_git to clone and snapshot a working tree for ingestion"
```

### Task 15: CRDT Relay (Yjs WebSocket Sync + Snapshot Endpoint)

**Files:**
- Create: crdt-relay/package.json
- Create: crdt-relay/.gitignore
- Create: crdt-relay/docs.js
- Create: crdt-relay/server.js
- Create: crdt-relay/snapshot.js
- Test: crdt-relay/relay.test.js

**Interfaces:**
- Consumes: none from earlier tasks. External packages only: `ws` (`WebSocket.Server`), `yjs` (`Y.Doc`, `Y.Text`), `y-websocket` (`setupWSConnection` from `y-websocket/bin/utils`, and `docs` exported from that same module; `WebsocketProvider` from `y-websocket` is used client side inside the test).
- Produces: a websocket sync endpoint per room, reachable at `ws://localhost:<PORT>/<room>` where `PORT` is `process.env.PORT` or `1234`, and `room` is a string such as an artifact id combined with a branch name (for example `artifact-1__main`); an HTTP `GET /snapshot/:room` endpoint on `process.env.SNAPSHOT_PORT` or `1235` returning a JSON body shaped as `{ text: string }`. Both the picked node test runner used here (Node built in `node:test`, not Jest) and later tasks rely on this exact shape.

Chosen test runner: the built in Node test runner (`node:test`), invoked with `node --test`, so no extra test dependency is required beyond the relay's own runtime packages.

- [ ] **Step 1: Scaffold the crdt-relay Node package**

Create `crdt-relay/package.json`:

```json
{
  "name": "crdt-relay",
  "version": "1.0.0",
  "private": true,
  "description": "Yjs CRDT relay and snapshot bridge for Git for Research",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "test": "node --test relay.test.js"
  },
  "dependencies": {
    "ws": "^8.16.0",
    "yjs": "^13.6.10",
    "y-websocket": "^1.5.0"
  }
}
```

Create `crdt-relay/.gitignore`:

```
node_modules/
```

Run:

```bash
cd ~/devcopilot/git-for-research/crdt-relay && npm install
```

Confirm the command exits with status 0 and that `crdt-relay/node_modules/` and `crdt-relay/package-lock.json` now exist on disk.

- [ ] **Step 2: Commit the package scaffold**

```bash
cd ~/devcopilot/git-for-research && git add crdt-relay/package.json crdt-relay/package-lock.json crdt-relay/.gitignore && git commit -m "Scaffold crdt-relay Node package with ws, yjs, and y-websocket dependencies"
```

- [ ] **Step 3: Write a failing test for two-client CRDT sync**

Create `crdt-relay/relay.test.js`:

```js
process.env.PORT = '31234';

const test = require('node:test');
const assert = require('node:assert/strict');
const WebSocket = require('ws');
const Y = require('yjs');
const { WebsocketProvider } = require('y-websocket');

require('./server');

function waitForSync(provider) {
  return new Promise((resolve) => {
    provider.on('sync', (isSynced) => {
      if (isSynced) {
        resolve();
      }
    });
  });
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

test('two clients in the same room converge on the same content via CRDT sync', async () => {
  const room = 'artifact-1__main';

  const docA = new Y.Doc();
  const providerA = new WebsocketProvider(`ws://localhost:${process.env.PORT}`, room, docA, {
    WebSocketPolyfill: WebSocket,
  });

  const docB = new Y.Doc();
  const providerB = new WebsocketProvider(`ws://localhost:${process.env.PORT}`, room, docB, {
    WebSocketPolyfill: WebSocket,
  });

  await Promise.all([waitForSync(providerA), waitForSync(providerB)]);

  const textA = docA.getText('content');
  textA.insert(0, 'hello from client A');

  await wait(300);

  const textB = docB.getText('content');
  assert.equal(textB.toString(), 'hello from client A');

  providerA.destroy();
  providerB.destroy();
});
```

- [ ] **Step 4: Run the test and confirm it fails**

```bash
cd ~/devcopilot/git-for-research && node --test crdt-relay/relay.test.js
```

Expected failure: the file fails to load because `crdt-relay/server.js` does not exist yet, with output containing `Cannot find module './server'` and a non-zero exit status with zero tests passing.

- [ ] **Step 5: Implement the shared doc registry and the websocket sync server**

Create `crdt-relay/docs.js`:

```js
const { docs } = require('y-websocket/bin/utils');

module.exports = { docs };
```

Create `crdt-relay/server.js`:

```js
const http = require('http');
const WebSocket = require('ws');
const { setupWSConnection } = require('y-websocket/bin/utils');

const PORT = process.env.PORT || 1234;

const server = http.createServer((request, response) => {
  response.writeHead(200, { 'Content-Type': 'text/plain' });
  response.end('crdt-relay ok');
});

const wss = new WebSocket.Server({ server });

wss.on('connection', (conn, req) => {
  setupWSConnection(conn, req);
});

server.listen(PORT, () => {
  console.log(`crdt-relay websocket server listening on port ${PORT}`);
});

module.exports = { server, wss };
```

- [ ] **Step 6: Run the test and confirm it passes**

```bash
cd ~/devcopilot/git-for-research && node --test crdt-relay/relay.test.js
```

Expected: output reports `# pass 1` and `# fail 0`.

- [ ] **Step 7: Commit the sync server**

```bash
cd ~/devcopilot/git-for-research && git add crdt-relay/docs.js crdt-relay/server.js crdt-relay/relay.test.js && git commit -m "Implement crdt-relay websocket sync server with shared Y.Doc registry"
```

- [ ] **Step 8: Extend the test with a failing snapshot endpoint test**

Replace `crdt-relay/relay.test.js` with:

```js
process.env.PORT = '31234';
process.env.SNAPSHOT_PORT = '31235';

const test = require('node:test');
const assert = require('node:assert/strict');
const WebSocket = require('ws');
const Y = require('yjs');
const { WebsocketProvider } = require('y-websocket');

require('./server');
require('./snapshot');

function waitForSync(provider) {
  return new Promise((resolve) => {
    provider.on('sync', (isSynced) => {
      if (isSynced) {
        resolve();
      }
    });
  });
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

test('two clients in the same room converge on the same content via CRDT sync', async () => {
  const room = 'artifact-1__main';

  const docA = new Y.Doc();
  const providerA = new WebsocketProvider(`ws://localhost:${process.env.PORT}`, room, docA, {
    WebSocketPolyfill: WebSocket,
  });

  const docB = new Y.Doc();
  const providerB = new WebsocketProvider(`ws://localhost:${process.env.PORT}`, room, docB, {
    WebSocketPolyfill: WebSocket,
  });

  await Promise.all([waitForSync(providerA), waitForSync(providerB)]);

  const textA = docA.getText('content');
  textA.insert(0, 'hello from client A');

  await wait(300);

  const textB = docB.getText('content');
  assert.equal(textB.toString(), 'hello from client A');

  providerA.destroy();
  providerB.destroy();
});

test('the snapshot endpoint returns the current text for a room', async () => {
  const room = 'artifact-2__main';

  const doc = new Y.Doc();
  const provider = new WebsocketProvider(`ws://localhost:${process.env.PORT}`, room, doc, {
    WebSocketPolyfill: WebSocket,
  });

  await waitForSync(provider);

  const text = doc.getText('content');
  text.insert(0, 'snapshot me');

  await wait(300);

  const response = await fetch(`http://localhost:${process.env.SNAPSHOT_PORT}/snapshot/${room}`);
  const body = await response.json();

  assert.equal(body.text, 'snapshot me');

  provider.destroy();
});
```

- [ ] **Step 9: Run the test and confirm it fails**

```bash
cd ~/devcopilot/git-for-research && node --test crdt-relay/relay.test.js
```

Expected failure: the file fails to load because `crdt-relay/snapshot.js` does not exist yet, with output containing `Cannot find module './snapshot'`.

- [ ] **Step 10: Implement the snapshot HTTP endpoint**

Create `crdt-relay/snapshot.js`:

```js
const http = require('http');
const { docs } = require('./docs');

const SNAPSHOT_PORT = process.env.SNAPSHOT_PORT || 1235;

function textForRoom(room) {
  const doc = docs.get(room);
  if (!doc) {
    return '';
  }
  const ytext = doc.getText('content');
  return ytext.toString();
}

const server = http.createServer((req, res) => {
  const match = req.url.match(/^\/snapshot\/([^/?]+)/);
  if (!match) {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'not found' }));
    return;
  }
  const room = decodeURIComponent(match[1]);
  const text = textForRoom(room);
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ text }));
});

server.listen(SNAPSHOT_PORT, () => {
  console.log(`crdt-relay snapshot server listening on port ${SNAPSHOT_PORT}`);
});

module.exports = { server, textForRoom };
```

- [ ] **Step 11: Run the test and confirm it passes**

```bash
cd ~/devcopilot/git-for-research && node --test crdt-relay/relay.test.js
```

Expected: output reports `# pass 2` and `# fail 0`.

- [ ] **Step 12: Commit the snapshot endpoint**

```bash
cd ~/devcopilot/git-for-research && git add crdt-relay/snapshot.js crdt-relay/relay.test.js && git commit -m "Add HTTP snapshot endpoint to crdt-relay backed by the shared doc registry"
```

### Task 16: Snapshot Bridge and Last Seen Tracking

**Files:**
- Create: backend/app/crdt/__init__.py
- Create: backend/app/crdt/snapshot_bridge.py
- Create: backend/app/crdt/last_seen.py
- Test: backend/tests/crdt/test_snapshot_bridge.py
- Test: backend/tests/crdt/test_last_seen.py

**Interfaces:**
- Consumes: `DagVersionedArtifact(session, artifact_id, tokenizer)` with method `commit(content, author, message, parent_ref)` from `app.versioning.dag_adapter`; `get_session()` from `app.db.base`; `LastSeen(user_id, artifact_id, commit_ref)` and `Commit` from `app.db.models`; `get_branch_head(session, artifact_id, name)`, `get_commit(session, commit_id)`, and `update_branch_head(session, artifact_id, name, commit_id)` from `app.versioning.dag_store`; `tokenize_paragraphs` from `app.versioning.diff_engine`; the `Commit` row schema fields `id`, `artifact_id`, `parent_ids` (a list of parent commit ids, empty for a root commit), `blob_hash`, `author`, `message`, `created_at`. Tests assume a pytest fixture named `session` is already provided by `backend/tests/conftest.py` from earlier tasks, yielding a SQLAlchemy session usable with the models above.
- Produces: `commit_snapshot(session, artifact_id, branch_name, snapshot_text, author)` from `backend/app/crdt/snapshot_bridge.py`; `mark_seen(session, user_id, artifact_id, commit_ref)` and `get_changes_since(session, user_id, artifact_id, branch_name)` from `backend/app/crdt/last_seen.py`.

- [ ] **Step 1: Write a failing test for commit_snapshot**

Create `backend/tests/crdt/test_snapshot_bridge.py`:

```python
import uuid

from app.crdt.snapshot_bridge import commit_snapshot
from app.versioning.dag_store import get_branch_head, get_commit


def test_commit_snapshot_creates_commit_and_advances_branch_head(session):
    artifact_id = str(uuid.uuid4())
    branch_name = "main"

    assert get_branch_head(session, artifact_id, branch_name) is None

    first_ref = commit_snapshot(
        session, artifact_id, branch_name, "Paragraph one.", "user-1"
    )

    assert get_branch_head(session, artifact_id, branch_name) == first_ref
    first_commit = get_commit(session, first_ref)
    assert first_commit.parent_ids == []
    assert first_commit.message == "Live edit snapshot"

    second_ref = commit_snapshot(
        session,
        artifact_id,
        branch_name,
        "Paragraph one.\n\nParagraph two.",
        "user-1",
    )

    assert second_ref != first_ref
    assert get_branch_head(session, artifact_id, branch_name) == second_ref
    second_commit = get_commit(session, second_ref)
    assert second_commit.parent_ids == [first_ref]
```

- [ ] **Step 2: Run the test and confirm it fails**

```bash
cd ~/devcopilot/git-for-research/backend && pytest tests/crdt/test_snapshot_bridge.py -v
```

Expected failure: collection error containing `ModuleNotFoundError: No module named 'app.crdt'`.

- [ ] **Step 3: Implement the crdt package and snapshot_bridge**

Create `backend/app/crdt/__init__.py`:

```python
```

Create `backend/app/crdt/snapshot_bridge.py`:

```python
from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import get_branch_head, update_branch_head
from app.versioning.diff_engine import tokenize_paragraphs


def commit_snapshot(
    session, artifact_id: str, branch_name: str, snapshot_text: str, author: str
) -> str:
    parent_ref = get_branch_head(session, artifact_id, branch_name)
    artifact = DagVersionedArtifact(session, artifact_id, tokenize_paragraphs)
    new_commit_ref = artifact.commit(
        snapshot_text, author, "Live edit snapshot", parent_ref
    )
    update_branch_head(session, artifact_id, branch_name, new_commit_ref)
    return new_commit_ref
```

- [ ] **Step 4: Run the test and confirm it passes**

```bash
cd ~/devcopilot/git-for-research/backend && pytest tests/crdt/test_snapshot_bridge.py -v
```

Expected: output reports `1 passed`.

- [ ] **Step 5: Commit the snapshot bridge**

```bash
cd ~/devcopilot/git-for-research && git add backend/app/crdt/__init__.py backend/app/crdt/snapshot_bridge.py backend/tests/crdt/test_snapshot_bridge.py && git commit -m "Add snapshot_bridge to commit live CRDT snapshots into the version DAG"
```

- [ ] **Step 6: Write failing tests for last_seen tracking**

Create `backend/tests/crdt/test_last_seen.py`:

```python
import uuid

from app.crdt.last_seen import get_changes_since, mark_seen
from app.crdt.snapshot_bridge import commit_snapshot


def test_get_changes_since_with_no_last_seen_returns_full_history(session):
    artifact_id = str(uuid.uuid4())
    branch_name = "main"

    commit_snapshot(session, artifact_id, branch_name, "Paragraph one.", "user-1")
    commit_snapshot(
        session,
        artifact_id,
        branch_name,
        "Paragraph one.\n\nParagraph two.",
        "user-1",
    )

    changes = get_changes_since(session, "user-1", artifact_id, branch_name)

    assert len(changes) == 2
    assert changes[0].parent_ids == []
    assert changes[1].parent_ids == [changes[0].id]


def test_get_changes_since_after_mark_seen_returns_only_new_commits(session):
    artifact_id = str(uuid.uuid4())
    branch_name = "main"

    first_ref = commit_snapshot(session, artifact_id, branch_name, "Paragraph one.", "user-1")
    mark_seen(session, "user-1", artifact_id, first_ref)

    second_ref = commit_snapshot(
        session,
        artifact_id,
        branch_name,
        "Paragraph one.\n\nParagraph two.",
        "user-1",
    )

    changes = get_changes_since(session, "user-1", artifact_id, branch_name)

    assert len(changes) == 1
    assert changes[0].id == second_ref
```

- [ ] **Step 7: Run the tests and confirm they fail**

```bash
cd ~/devcopilot/git-for-research/backend && pytest tests/crdt/test_last_seen.py -v
```

Expected failure: collection error containing `ModuleNotFoundError: No module named 'app.crdt.last_seen'`.

- [ ] **Step 8: Implement last_seen tracking**

Create `backend/app/crdt/last_seen.py`:

```python
from app.db.models import LastSeen
from app.versioning.dag_store import get_branch_head, get_commit


def mark_seen(session, user_id: str, artifact_id: str, commit_ref: str) -> None:
    existing = (
        session.query(LastSeen)
        .filter(LastSeen.user_id == user_id, LastSeen.artifact_id == artifact_id)
        .one_or_none()
    )
    if existing is None:
        existing = LastSeen(
            user_id=user_id, artifact_id=artifact_id, commit_ref=commit_ref
        )
        session.add(existing)
    else:
        existing.commit_ref = commit_ref
    session.commit()


def get_changes_since(
    session, user_id: str, artifact_id: str, branch_name: str
) -> list:
    head_ref = get_branch_head(session, artifact_id, branch_name)
    if head_ref is None:
        return []

    last_seen_row = (
        session.query(LastSeen)
        .filter(LastSeen.user_id == user_id, LastSeen.artifact_id == artifact_id)
        .one_or_none()
    )
    stop_ref = last_seen_row.commit_ref if last_seen_row is not None else None

    commits = []
    current_ref = head_ref
    while current_ref is not None and current_ref != stop_ref:
        commit = get_commit(session, current_ref)
        if commit is None:
            break
        commits.append(commit)
        current_ref = commit.parent_ids[0] if commit.parent_ids else None

    commits.reverse()
    return commits
```

- [ ] **Step 9: Run the tests and confirm they pass**

```bash
cd ~/devcopilot/git-for-research/backend && pytest tests/crdt/test_last_seen.py -v
```

Expected: output reports `2 passed`.

- [ ] **Step 10: Commit last_seen tracking**

```bash
cd ~/devcopilot/git-for-research && git add backend/app/crdt/last_seen.py backend/tests/crdt/test_last_seen.py && git commit -m "Add last_seen tracking so viewers see only commits made since their last visit"
```

### Task 17: Embeddings and Chunking

**Files:**
- Create: backend/app/retrieval/__init__.py
- Create: backend/app/retrieval/embeddings.py
- Create: backend/app/retrieval/chunker.py
- Test: backend/tests/retrieval/test_embeddings.py
- Test: backend/tests/retrieval/test_chunker.py

**Interfaces:**
- Consumes: `tokenize_paragraphs(text: str) -> list[str]` and `tokenize_messages(content_json: str) -> list[str]`, both from `app.versioning.diff_engine`, exactly as produced by an earlier task.
- Produces: `embed_text(text: str) -> list[float]` from `backend/app/retrieval/embeddings.py`. `chunk_prose(text: str) -> list[str]`, `chunk_messages(content_json: str) -> list[str]`, `chunk_code(files: dict[str, str]) -> list[tuple[str, str]]` from `backend/app/retrieval/chunker.py`.

- [ ] **Step 1: Write a failing test for embed_text**

Create `backend/tests/retrieval/test_embeddings.py`:

```python
from app.retrieval.embeddings import embed_text


def test_embed_text_returns_384_length_float_vector():
    vector = embed_text("The lab confirmed the reaction rate increased with temperature.")
    assert isinstance(vector, list)
    assert len(vector) == 384
    assert all(isinstance(value, float) for value in vector)


def test_embed_text_is_deterministic_for_identical_input():
    text = "Photosynthesis converts light energy into chemical energy."
    first = embed_text(text)
    second = embed_text(text)
    assert first == second
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
cd backend && python -m pytest tests/retrieval/test_embeddings.py -v
```

Expected failure text: `ModuleNotFoundError: No module named 'app.retrieval'`

- [ ] **Step 3: Install the embedding dependency and write the minimal implementation**

Run:

```bash
pip install sentence-transformers
```

Create `backend/app/retrieval/__init__.py` (empty file, makes the directory a package).

Create `backend/app/retrieval/embeddings.py`:

```python
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> list[float]:
    encoded = _model.encode(text)
    return encoded.tolist()
```

- [ ] **Step 4: Run the test again and confirm it passes**

Run:

```bash
cd backend && python -m pytest tests/retrieval/test_embeddings.py -v
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/retrieval/__init__.py backend/app/retrieval/embeddings.py backend/tests/retrieval/test_embeddings.py
git commit -m "Add local sentence-transformers embedding helper"
```

- [ ] **Step 6: Write failing tests for chunk_prose and chunk_messages**

Create `backend/tests/retrieval/test_chunker.py`:

```python
import json

from app.versioning.diff_engine import tokenize_paragraphs, tokenize_messages
from app.retrieval.chunker import chunk_prose, chunk_messages


def test_chunk_prose_reuses_paragraph_tokenizer_and_produces_expected_count():
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunks = chunk_prose(text)
    assert chunks == tokenize_paragraphs(text)
    assert len(chunks) == 3


def test_chunk_messages_reuses_message_tokenizer_and_produces_expected_count():
    content_json = json.dumps(
        [
            {"role": "user", "text": "Hello there"},
            {"role": "assistant", "text": "Hi, how can I help?"},
        ]
    )
    chunks = chunk_messages(content_json)
    assert chunks == tokenize_messages(content_json)
    assert len(chunks) == 2
```

- [ ] **Step 7: Run the test and confirm it fails**

Run:

```bash
cd backend && python -m pytest tests/retrieval/test_chunker.py -v
```

Expected failure text: `ModuleNotFoundError: No module named 'app.retrieval.chunker'`

- [ ] **Step 8: Write the minimal implementation for chunk_prose and chunk_messages**

Create `backend/app/retrieval/chunker.py`:

```python
from app.versioning.diff_engine import tokenize_paragraphs, tokenize_messages


def chunk_prose(text: str) -> list[str]:
    return tokenize_paragraphs(text)


def chunk_messages(content_json: str) -> list[str]:
    return tokenize_messages(content_json)
```

- [ ] **Step 9: Run the test again and confirm it passes**

Run:

```bash
cd backend && python -m pytest tests/retrieval/test_chunker.py -v
```

Expected: both tests pass.

- [ ] **Step 10: Commit**

```bash
git add backend/app/retrieval/chunker.py backend/tests/retrieval/test_chunker.py
git commit -m "Add prose and chat chunkers that reuse the diff engine tokenizers"
```

- [ ] **Step 11: Write a failing test for chunk_code**

Append to `backend/tests/retrieval/test_chunker.py`:

```python
from app.retrieval.chunker import chunk_code


def test_chunk_code_extracts_named_top_level_functions():
    files = {
        "utils.py": (
            "def foo():\n"
            "    return 1\n"
            "\n"
            "\n"
            "def bar():\n"
            "    return 2\n"
        )
    }
    chunks = chunk_code(files)
    assert len(chunks) == 2
    names = [name for name, _ in chunks]
    assert names == ["utils.py::foo", "utils.py::bar"]
    assert "return 1" in chunks[0][1]
    assert "return 2" in chunks[1][1]
```

- [ ] **Step 12: Run the test and confirm it fails**

Run:

```bash
cd backend && python -m pytest tests/retrieval/test_chunker.py -v
```

Expected failure text: `ImportError: cannot import name 'chunk_code' from 'app.retrieval.chunker'`

- [ ] **Step 13: Install tree-sitter support and add the chunk_code implementation**

Run:

```bash
pip install tree_sitter_languages
```

Append to `backend/app/retrieval/chunker.py`:

```python
from tree_sitter_languages import get_parser

_TOP_LEVEL_NODE_TYPES = ("function_definition", "class_definition")


def _extract_python_chunks(filename: str, source: str) -> list[tuple[str, str]]:
    parser = get_parser("python")
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)
    chunks: list[tuple[str, str]] = []
    for node in tree.root_node.children:
        if node.type not in _TOP_LEVEL_NODE_TYPES:
            continue
        name_node = node.child_by_field_name("name")
        if name_node is None:
            continue
        name = source_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8")
        text = source_bytes[node.start_byte : node.end_byte].decode("utf-8")
        chunks.append((f"{filename}::{name}", text))
    return chunks


def chunk_code(files: dict[str, str]) -> list[tuple[str, str]]:
    all_chunks: list[tuple[str, str]] = []
    for filename, source in files.items():
        if filename.endswith(".py"):
            all_chunks.extend(_extract_python_chunks(filename, source))
        else:
            all_chunks.append((filename, source))
    return all_chunks
```

- [ ] **Step 14: Run the test again and confirm it passes**

Run:

```bash
cd backend && python -m pytest tests/retrieval/test_chunker.py -v
```

Expected: all three tests in the file pass.

- [ ] **Step 15: Commit**

```bash
git add backend/app/retrieval/chunker.py backend/tests/retrieval/test_chunker.py
git commit -m "Add tree-sitter based code chunker for top-level functions and classes"
```

### Task 18: Retrieval Query

**Files:**
- Create: backend/app/retrieval/query.py
- Test: backend/tests/retrieval/test_query.py

**Interfaces:**
- Consumes: `get_session()` from `backend/app/db/base.py`. `Chunk(id, artifact_id, commit_ref, text, embedding, span)` from `backend/app/db/models.py`. `embed_text(text: str) -> list[float]` from `backend/app/retrieval/embeddings.py` (Task 17).
- Produces: `index_chunks(session, artifact_id: str, commit_ref: str, texts: list[str]) -> list[str]` and `similarity_search(session, query: str, top_k: int = 5) -> list[dict]` from `backend/app/retrieval/query.py`.

- [ ] **Step 1: Write a failing test for index_chunks**

Create `backend/tests/retrieval/test_query.py`:

```python
import uuid

from app.db.base import get_session
from app.db.models import Chunk
from app.retrieval.query import index_chunks


def test_index_chunks_creates_distinct_chunk_rows():
    artifact_id = str(uuid.uuid4())
    commit_ref = str(uuid.uuid4())
    texts = [
        "The cat sat on the mat.",
        "Quarterly revenue grew by ten percent this year.",
        "The dog played in the park all afternoon.",
    ]
    with get_session() as session:
        chunk_ids = index_chunks(session, artifact_id, commit_ref, texts)
        assert len(chunk_ids) == 3
        assert len(set(chunk_ids)) == 3
        stored = session.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
        assert len(stored) == 3
        assert {row.artifact_id for row in stored} == {artifact_id}
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
cd backend && python -m pytest tests/retrieval/test_query.py -v
```

Expected failure text: `ModuleNotFoundError: No module named 'app.retrieval.query'`

- [ ] **Step 3: Write the minimal implementation for index_chunks**

Create `backend/app/retrieval/query.py`:

```python
import uuid

from app.db.models import Chunk
from app.retrieval.embeddings import embed_text


def index_chunks(session, artifact_id: str, commit_ref: str, texts: list[str]) -> list[str]:
    chunk_ids: list[str] = []
    for index, text in enumerate(texts):
        chunk_id = str(uuid.uuid4())
        chunk = Chunk(
            id=chunk_id,
            artifact_id=artifact_id,
            commit_ref=commit_ref,
            text=text,
            embedding=embed_text(text),
            span=str(index),
        )
        session.add(chunk)
        chunk_ids.append(chunk_id)
    session.commit()
    return chunk_ids
```

- [ ] **Step 4: Run the test again and confirm it passes**

Run:

```bash
cd backend && python -m pytest tests/retrieval/test_query.py -v
```

Expected: the index_chunks test passes.

- [ ] **Step 5: Commit**

```bash
git add backend/app/retrieval/query.py backend/tests/retrieval/test_query.py
git commit -m "Add pgvector-backed chunk indexing"
```

- [ ] **Step 6: Write a failing test for similarity_search**

Append to `backend/tests/retrieval/test_query.py`:

```python
from app.retrieval.query import similarity_search


def test_similarity_search_ranks_semantically_closest_chunk_first():
    artifact_id = str(uuid.uuid4())
    commit_ref = str(uuid.uuid4())
    texts = [
        "The cat sat on the mat.",
        "Quarterly revenue grew by ten percent this year.",
        "The dog played in the park all afternoon.",
    ]
    with get_session() as session:
        index_chunks(session, artifact_id, commit_ref, texts)
        results = similarity_search(session, "A feline is resting on a rug.", top_k=3)
        assert results[0]["text"] == "The cat sat on the mat."
        assert results[0]["artifact_id"] == artifact_id
        assert results[0]["commit_ref"] == commit_ref
        assert "chunk_id" in results[0]
        assert "score" in results[0]
```

- [ ] **Step 7: Run the test and confirm it fails**

Run:

```bash
cd backend && python -m pytest tests/retrieval/test_query.py -v
```

Expected failure text: `ImportError: cannot import name 'similarity_search' from 'app.retrieval.query'`

- [ ] **Step 8: Write the minimal implementation for similarity_search**

Append to `backend/app/retrieval/query.py`:

```python
def similarity_search(session, query: str, top_k: int = 5) -> list[dict]:
    query_embedding = embed_text(query)
    distance = Chunk.embedding.cosine_distance(query_embedding)
    rows = (
        session.query(Chunk, distance.label("distance"))
        .order_by(distance)
        .limit(top_k)
        .all()
    )
    results: list[dict] = []
    for chunk, score in rows:
        results.append(
            {
                "chunk_id": chunk.id,
                "text": chunk.text,
                "artifact_id": chunk.artifact_id,
                "commit_ref": chunk.commit_ref,
                "score": float(score),
            }
        )
    return results
```

- [ ] **Step 9: Run the test again and confirm it passes**

Run:

```bash
cd backend && python -m pytest tests/retrieval/test_query.py -v
```

Expected: both tests in the file pass.

- [ ] **Step 10: Commit**

```bash
git add backend/app/retrieval/query.py backend/tests/retrieval/test_query.py
git commit -m "Add cosine-similarity chunk search over pgvector embeddings"
```

### Task 19: Provenance Graph

**Files:**
- Create: backend/app/retrieval/provenance.py
- Test: backend/tests/retrieval/test_provenance.py

**Interfaces:**
- Consumes: `get_session()` from `backend/app/db/base.py`. `ProvenanceEdge(id, from_chunk_id, to_chunk_id, relation)` from `backend/app/db/models.py`. `index_chunks(session, artifact_id, commit_ref, texts) -> list[str]` from `backend/app/retrieval/query.py` (Task 18), used in tests to create real chunk rows to link.
- Produces: `add_provenance_edge(session, from_chunk_id: str, to_chunk_id: str, relation: str) -> None` and `trace_provenance(session, chunk_id: str) -> list[dict]` from `backend/app/retrieval/provenance.py`.

- [ ] **Step 1: Write failing tests covering the chain, empty, and cycle cases**

Create `backend/tests/retrieval/test_provenance.py`:

```python
import uuid

from app.db.base import get_session
from app.retrieval.query import index_chunks
from app.retrieval.provenance import add_provenance_edge, trace_provenance


def test_trace_provenance_returns_two_hop_chain_in_order():
    with get_session() as session:
        artifact_id = str(uuid.uuid4())
        commit_ref = str(uuid.uuid4())
        chunk_ids = index_chunks(
            session,
            artifact_id,
            commit_ref,
            ["Claim A", "Source B", "Source C"],
        )
        chunk_a, chunk_b, chunk_c = chunk_ids
        add_provenance_edge(session, chunk_a, chunk_b, "cites")
        add_provenance_edge(session, chunk_b, chunk_c, "supports")

        chain = trace_provenance(session, chunk_a)

        assert chain == [
            {"chunk_id": chunk_b, "relation": "cites"},
            {"chunk_id": chunk_c, "relation": "supports"},
        ]


def test_trace_provenance_returns_empty_list_when_no_edges_exist():
    with get_session() as session:
        artifact_id = str(uuid.uuid4())
        commit_ref = str(uuid.uuid4())
        chunk_ids = index_chunks(session, artifact_id, commit_ref, ["Standalone claim"])
        chunk_id = chunk_ids[0]

        chain = trace_provenance(session, chunk_id)

        assert chain == []


def test_trace_provenance_handles_a_cycle_without_infinite_loop():
    with get_session() as session:
        artifact_id = str(uuid.uuid4())
        commit_ref = str(uuid.uuid4())
        chunk_ids = index_chunks(session, artifact_id, commit_ref, ["Claim A", "Claim B"])
        chunk_a, chunk_b = chunk_ids
        add_provenance_edge(session, chunk_a, chunk_b, "cites")
        add_provenance_edge(session, chunk_b, chunk_a, "cites")

        chain = trace_provenance(session, chunk_a)

        assert chain == [{"chunk_id": chunk_b, "relation": "cites"}]
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run:

```bash
cd backend && python -m pytest tests/retrieval/test_provenance.py -v
```

Expected failure text: `ModuleNotFoundError: No module named 'app.retrieval.provenance'`

- [ ] **Step 3: Write the minimal implementation**

Create `backend/app/retrieval/provenance.py`:

```python
import uuid

from app.db.models import ProvenanceEdge


def add_provenance_edge(session, from_chunk_id: str, to_chunk_id: str, relation: str) -> None:
    edge = ProvenanceEdge(
        id=str(uuid.uuid4()),
        from_chunk_id=from_chunk_id,
        to_chunk_id=to_chunk_id,
        relation=relation,
    )
    session.add(edge)
    session.commit()


def trace_provenance(session, chunk_id: str) -> list[dict]:
    chain: list[dict] = []
    visited: set[str] = {chunk_id}
    current_id = chunk_id
    while True:
        edge = (
            session.query(ProvenanceEdge)
            .filter(ProvenanceEdge.from_chunk_id == current_id)
            .first()
        )
        if edge is None:
            break
        if edge.to_chunk_id in visited:
            break
        chain.append({"chunk_id": edge.to_chunk_id, "relation": edge.relation})
        visited.add(edge.to_chunk_id)
        current_id = edge.to_chunk_id
    return chain
```

- [ ] **Step 4: Run the tests again and confirm they pass**

Run:

```bash
cd backend && python -m pytest tests/retrieval/test_provenance.py -v
```

Expected: all three tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/retrieval/provenance.py backend/tests/retrieval/test_provenance.py
git commit -m "Add provenance edge recording and cycle-safe recursive trace"
```

### Task 20: Merge Request API

**Files:**
- Create: backend/app/collab/merge_requests.py
- Test: backend/tests/collab/test_merge_requests.py

**Interfaces:**
- Consumes: backend/app/db/base.py get_session(); backend/app/db/models.py MergeRequest(id,artifact_id,source_branch,target_branch,status,base_commit_ref); backend/app/versioning/dag_adapter.py class DagVersionedArtifact(session,artifact_id,tokenizer) with diff(ref_a,ref_b), merge(base_ref,ours_ref,theirs_ref), branch(name,from_ref), commit(content,author,message,parent_ref), get_content(ref), branch_head(name); backend/app/versioning/dag_store.py get_branch_head(session,artifact_id,name) (returns None if the branch does not exist), get_commit(session,commit_id), update_branch_head(session,artifact_id,name,new_commit_id); backend/app/versioning/merge_engine.py diff3_merge(base_tokens,ours_tokens,theirs_tokens) -> {"merged_tokens": list[str], "conflicts": list[dict]} (merged_tokens stays index-aligned with the base paragraphs, including a placeholder at each conflict position)
- Produces: create_merge_request(session, artifact_id: str, source_branch: str, target_branch: str) -> str; get_merge_request_diff(session, mr_id: str) -> dict; merge_merge_request(session, mr_id: str, resolutions: dict | None) -> bool; reject_merge_request(session, mr_id: str) -> None

- [ ] **Step 1: write failing test for create_merge_request**

Create the test file with the first test, asserting that opening a merge request records the correct base commit ref and status.

```python
from app.collab.merge_requests import create_merge_request
from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import get_branch_head
from app.db.models import MergeRequest


def _paragraph_tokenizer(text: str):
    return text.split("\n\n")


def test_create_merge_request_records_base_commit_ref(db_session):
    artifact_id = "artifact-mr-1"
    artifact = DagVersionedArtifact(db_session, artifact_id, _paragraph_tokenizer)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-a", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )

    mr_id = create_merge_request(db_session, artifact_id, "feature-a", "main")

    mr = db_session.get(MergeRequest, mr_id)
    assert mr is not None
    assert mr.artifact_id == artifact_id
    assert mr.source_branch == "feature-a"
    assert mr.target_branch == "main"
    assert mr.status == "open"
    assert mr.base_commit_ref == get_branch_head(db_session, artifact_id, "main")
```

- [ ] **Step 2: run test and confirm it fails**

Run:

```bash
pytest backend/tests/collab/test_merge_requests.py::test_create_merge_request_records_base_commit_ref -v
```

Expected failure output:

```
ModuleNotFoundError: No module named 'app.collab.merge_requests'
```

- [ ] **Step 3: implement create_merge_request**

Write the initial implementation module. The merge base must be the true common ancestor commit of the two branches, not simply "whatever the target branch currently points at" — if the target branch has advanced with its own commits since the source branch forked, using the target's current head as the base would make `diff3_merge` see the target's own changes as part of the "base", silently hiding real conflicts. `_find_common_ancestor` walks each branch's first-parent chain back to the root and returns the first commit id that appears in both chains.

```python
import uuid

from app.db.models import MergeRequest
from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import get_branch_head, get_commit, update_branch_head
from app.versioning.merge_engine import diff3_merge


def _paragraph_tokenizer(text: str):
    return text.split("\n\n")


def _ancestor_chain(session, ref: str) -> list:
    chain = []
    current_ref = ref
    while current_ref is not None:
        chain.append(current_ref)
        commit = get_commit(session, current_ref)
        current_ref = commit.parent_ids[0] if commit.parent_ids else None
    return chain


def _find_common_ancestor(session, ref_a: str, ref_b: str) -> str:
    chain_a = _ancestor_chain(session, ref_a)
    chain_b_set = set(_ancestor_chain(session, ref_b))
    for commit_id in chain_a:
        if commit_id in chain_b_set:
            return commit_id
    return None


def create_merge_request(session, artifact_id: str, source_branch: str, target_branch: str) -> str:
    target_head = get_branch_head(session, artifact_id, target_branch)
    source_head = get_branch_head(session, artifact_id, source_branch)
    base_commit_ref = _find_common_ancestor(session, target_head, source_head)
    mr_id = str(uuid.uuid4())
    mr = MergeRequest(
        id=mr_id,
        artifact_id=artifact_id,
        source_branch=source_branch,
        target_branch=target_branch,
        status="open",
        base_commit_ref=base_commit_ref,
    )
    session.add(mr)
    session.commit()
    return mr_id
```

- [ ] **Step 4: run test and confirm it passes**

Run:

```bash
pytest backend/tests/collab/test_merge_requests.py::test_create_merge_request_records_base_commit_ref -v
```

Expected output: `1 passed`

- [ ] **Step 5: commit**

```bash
git add backend/app/collab/merge_requests.py backend/tests/collab/test_merge_requests.py
git commit -m "Add create_merge_request that snapshots target branch head as base commit ref"
```

- [ ] **Step 6: write failing test for get_merge_request_diff with no conflicts**

Append a test for the non-conflicting diff preview.

```python
def test_get_merge_request_diff_reports_no_conflicts_for_disjoint_edits(db_session):
    from app.collab.merge_requests import create_merge_request, get_merge_request_diff
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-2"
    artifact = DagVersionedArtifact(db_session, artifact_id, _paragraph_tokenizer)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-b", root)

    # Committing alone does not move a branch head — DagVersionedArtifact.commit
    # only appends a commit object; the branch pointer must be advanced
    # explicitly so later branch-head lookups see this edit.
    feature_commit = artifact.commit(
        "Edited intro paragraph.\n\nBody paragraph.", "user-1", "edit intro", root
    )
    update_branch_head(db_session, artifact_id, "feature-b", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-b", "main")
    result = get_merge_request_diff(db_session, mr_id)

    assert result["conflicts"] == []
```

- [ ] **Step 7: run test and confirm it fails**

Run:

```bash
pytest backend/tests/collab/test_merge_requests.py::test_get_merge_request_diff_reports_no_conflicts_for_disjoint_edits -v
```

Expected failure output:

```
ImportError: cannot import name 'get_merge_request_diff' from 'app.collab.merge_requests'
```

- [ ] **Step 8: implement get_merge_request_diff**

Add the function to the module.

```python
def get_merge_request_diff(session, mr_id: str) -> dict:
    mr = session.get(MergeRequest, mr_id)
    artifact = DagVersionedArtifact(session, mr.artifact_id, _paragraph_tokenizer)

    base_content = artifact.get_content(mr.base_commit_ref)
    target_head = artifact.branch_head(mr.target_branch)
    source_head = artifact.branch_head(mr.source_branch)
    target_content = artifact.get_content(target_head)
    source_content = artifact.get_content(source_head)

    base_tokens = _paragraph_tokenizer(base_content)
    ours_tokens = _paragraph_tokenizer(target_content)
    theirs_tokens = _paragraph_tokenizer(source_content)

    return diff3_merge(base_tokens, ours_tokens, theirs_tokens)
```

- [ ] **Step 9: run test and confirm it passes**

Run:

```bash
pytest backend/tests/collab/test_merge_requests.py::test_get_merge_request_diff_reports_no_conflicts_for_disjoint_edits -v
```

Expected output: `1 passed`

- [ ] **Step 10: commit**

```bash
git add backend/app/collab/merge_requests.py backend/tests/collab/test_merge_requests.py
git commit -m "Add get_merge_request_diff as a non-mutating diff3 preview over branch heads"
```

- [ ] **Step 11: write failing test for merge_merge_request with no conflicts**

Append a test that a clean merge advances the target branch head and sets status merged.

```python
def test_merge_merge_request_advances_target_head_when_no_conflicts(db_session):
    from app.collab.merge_requests import create_merge_request, merge_merge_request
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-3"
    artifact = DagVersionedArtifact(db_session, artifact_id, _paragraph_tokenizer)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-c", root)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nEdited body paragraph.", "user-1", "edit body", root
    )
    update_branch_head(db_session, artifact_id, "feature-c", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-c", "main")
    old_head = get_branch_head(db_session, artifact_id, "main")

    result = merge_merge_request(db_session, mr_id, None)

    new_head = get_branch_head(db_session, artifact_id, "main")
    mr = db_session.get(MergeRequest, mr_id)

    assert result is True
    assert new_head != old_head
    assert mr.status == "merged"
    assert artifact.get_content(new_head) == "Intro paragraph.\n\nEdited body paragraph."
```

- [ ] **Step 12: run test and confirm it fails**

Run:

```bash
pytest backend/tests/collab/test_merge_requests.py::test_merge_merge_request_advances_target_head_when_no_conflicts -v
```

Expected failure output:

```
ImportError: cannot import name 'merge_merge_request' from 'app.collab.merge_requests'
```

- [ ] **Step 13: implement merge_merge_request and reject_merge_request**

Add both functions to the module. `artifact.merge(...)` returns a dict (from `DagVersionedArtifact.merge`), not a commit id string — in the no-conflict path it must be unpacked to read `result["merge_commit_id"]`. In the conflict-with-resolutions path, resolutions key into `diff_result["merged_tokens"]` by `position`, which `diff3_merge` keeps index-aligned with the base paragraphs (including a placeholder at each conflict position) specifically so this splicing works.

```python
def merge_merge_request(session, mr_id: str, resolutions=None) -> bool:
    mr = session.get(MergeRequest, mr_id)
    artifact = DagVersionedArtifact(session, mr.artifact_id, _paragraph_tokenizer)

    diff_result = get_merge_request_diff(session, mr_id)
    conflicts = diff_result["conflicts"]

    if conflicts and resolutions is None:
        return False

    target_head = artifact.branch_head(mr.target_branch)
    source_head = artifact.branch_head(mr.source_branch)

    if not conflicts:
        merge_result = artifact.merge(mr.base_commit_ref, target_head, source_head)
        merge_commit_id = merge_result["merge_commit_id"]
    else:
        merged_tokens = list(diff_result["merged_tokens"])
        for position, resolved_text in resolutions.items():
            merged_tokens[position] = resolved_text
        merge_content = "\n\n".join(merged_tokens)
        merge_commit_id = artifact.commit(
            merge_content, "user-1", "resolve merge conflicts", target_head
        )

    update_branch_head(session, mr.artifact_id, mr.target_branch, merge_commit_id)
    mr.status = "merged"
    session.commit()
    return True


def reject_merge_request(session, mr_id: str) -> None:
    mr = session.get(MergeRequest, mr_id)
    mr.status = "rejected"
    session.commit()
```

- [ ] **Step 14: run test and confirm it passes**

Run:

```bash
pytest backend/tests/collab/test_merge_requests.py::test_merge_merge_request_advances_target_head_when_no_conflicts -v
```

Expected output: `1 passed`

- [ ] **Step 15: commit**

```bash
git add backend/app/collab/merge_requests.py backend/tests/collab/test_merge_requests.py
git commit -m "Add merge_merge_request and reject_merge_request finalizing branch state"
```

- [ ] **Step 16: write failing test for conflicting merge blocked without resolutions**

Append a test with overlapping edits to the same paragraph, verifying the merge is blocked until resolutions are supplied.

```python
def test_merge_merge_request_blocks_on_conflict_until_resolved(db_session):
    from app.collab.merge_requests import (
        create_merge_request,
        get_merge_request_diff,
        merge_merge_request,
    )
    from app.versioning.dag_store import update_branch_head

    artifact_id = "artifact-mr-4"
    artifact = DagVersionedArtifact(db_session, artifact_id, _paragraph_tokenizer)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)
    artifact.branch("feature-d", root)

    main_commit = artifact.commit(
        "Intro paragraph.\n\nMain-edited body.", "user-1", "main edit", root
    )
    update_branch_head(db_session, artifact_id, "main", main_commit)

    feature_commit = artifact.commit(
        "Intro paragraph.\n\nFeature-edited body.", "user-1", "feature edit", root
    )
    update_branch_head(db_session, artifact_id, "feature-d", feature_commit)

    mr_id = create_merge_request(db_session, artifact_id, "feature-d", "main")

    diff_result = get_merge_request_diff(db_session, mr_id)
    assert len(diff_result["conflicts"]) == 1

    blocked = merge_merge_request(db_session, mr_id, None)
    mr = db_session.get(MergeRequest, mr_id)
    assert blocked is False
    assert mr.status == "open"

    conflict_position = diff_result["conflicts"][0]["position"]
    resolved = merge_merge_request(
        db_session, mr_id, {conflict_position: "Resolved merged body."}
    )
    mr = db_session.get(MergeRequest, mr_id)
    assert resolved is True
    assert mr.status == "merged"

    new_head = get_branch_head(db_session, artifact_id, "main")
    assert artifact.get_content(new_head) == "Intro paragraph.\n\nResolved merged body."
```

- [ ] **Step 17: run test and confirm it fails**

Run:

```bash
pytest backend/tests/collab/test_merge_requests.py::test_merge_merge_request_blocks_on_conflict_until_resolved -v
```

Expected failure output, because this test's edits (as first written, before the fix below) never called `update_branch_head`, so `main` and `feature-d` both still pointed at `root` and `get_merge_request_diff` compared identical content against itself:

```
AssertionError: assert 0 == 1
```

- [ ] **Step 18: add the missing branch head updates**

A commit created via `DagVersionedArtifact.commit(...)` does not move any branch pointer — only `update_branch_head` does. The test above already calls `update_branch_head` for both `main` and `feature-d` after each edit; this is the fix itself, applied directly in the test code in Step 16 rather than in `merge_requests.py`, since the bug was in the test's setup, not in `merge_merge_request` or `get_merge_request_diff`.

```python
# No production code change needed here: merge_merge_request and
# get_merge_request_diff both already read branch heads correctly via
# artifact.branch_head(...); the fix is calling update_branch_head after each
# commit in the test above, so those branch heads actually point at the
# edited content instead of both still pointing at `root`.
```

- [ ] **Step 19: run test and confirm it passes**

Run:

```bash
pytest backend/tests/collab/test_merge_requests.py::test_merge_merge_request_blocks_on_conflict_until_resolved -v
```

Expected output: `1 passed`

- [ ] **Step 20: commit**

```bash
git add backend/tests/collab/test_merge_requests.py
git commit -m "Add coverage for blocked and resolution-driven conflict merges"
```

### Task 21: Multi-Agent Editing Flow

**Files:**
- Create: backend/app/collab/agent_editor.py
- Test: backend/tests/collab/test_agent_editor.py

**Interfaces:**
- Consumes: backend/app/versioning/dag_adapter.py class DagVersionedArtifact(session,artifact_id,tokenizer) with branch_head(name), get_content(ref), branch(name,from_ref), commit(content,author,message,parent_ref); backend/app/collab/merge_requests.py create_merge_request(session,artifact_id,source_branch,target_branch)
- Produces: agent_edit(session, artifact_id: str, base_branch: str, instruction: str, llm_call) -> str

- [ ] **Step 1: write failing test for agent_edit creating a branch, commit, and merge request**

Create the test file with a deterministic fake llm_call.

```python
from app.collab.agent_editor import agent_edit
from app.versioning.dag_adapter import DagVersionedArtifact
from app.db.models import MergeRequest


def _paragraph_tokenizer(text: str):
    return text.split("\n\n")


def _fake_llm_call(instruction: str, current_content: str) -> str:
    return current_content + "\n\nAppended by agent."


def test_agent_edit_creates_branch_commit_and_open_merge_request(db_session):
    artifact_id = "artifact-agent-1"
    artifact = DagVersionedArtifact(db_session, artifact_id, _paragraph_tokenizer)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)

    mr_id = agent_edit(
        db_session, artifact_id, "main", "Append a closing remark.", _fake_llm_call
    )

    mr = db_session.get(MergeRequest, mr_id)
    assert mr is not None
    assert mr.status == "open"
    assert mr.target_branch == "main"
    assert mr.source_branch.startswith("agent-edit-")

    source_head = artifact.branch_head(mr.source_branch)
    source_content = artifact.get_content(source_head)
    assert source_content == "Intro paragraph.\n\nBody paragraph.\n\nAppended by agent."
```

- [ ] **Step 2: run test and confirm it fails**

Run:

```bash
pytest backend/tests/collab/test_agent_editor.py::test_agent_edit_creates_branch_commit_and_open_merge_request -v
```

Expected failure output:

```
ModuleNotFoundError: No module named 'app.collab.agent_editor'
```

- [ ] **Step 3: implement agent_edit**

Write the implementation module. `artifact.branch(...)` only creates the branch pointer at `base_head`; it does not move automatically when a later commit is made against that ref. The commit must be followed by an explicit `update_branch_head` call, or `mr.source_branch` would still point at `base_head` and the proposed edit would be invisible to anyone reading the branch.

```python
import uuid

from app.collab.merge_requests import create_merge_request
from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import update_branch_head


def _paragraph_tokenizer(text: str):
    return text.split("\n\n")


def agent_edit(session, artifact_id: str, base_branch: str, instruction: str, llm_call) -> str:
    artifact = DagVersionedArtifact(session, artifact_id, _paragraph_tokenizer)

    base_head = artifact.branch_head(base_branch)
    current_content = artifact.get_content(base_head)

    proposed_content = llm_call(instruction, current_content)

    suffix = uuid.uuid4().hex[:8]
    new_branch_name = f"agent-edit-{suffix}"
    artifact.branch(new_branch_name, base_head)

    new_commit_id = artifact.commit(proposed_content, "agent", instruction, base_head)
    update_branch_head(session, artifact_id, new_branch_name, new_commit_id)

    mr_id = create_merge_request(session, artifact_id, new_branch_name, base_branch)
    return mr_id
```

- [ ] **Step 4: run test and confirm it passes**

Run:

```bash
pytest backend/tests/collab/test_agent_editor.py::test_agent_edit_creates_branch_commit_and_open_merge_request -v
```

Expected output: `1 passed`

- [ ] **Step 5: commit**

```bash
git add backend/app/collab/agent_editor.py backend/tests/collab/test_agent_editor.py
git commit -m "Add agent_edit flow that proposes changes on a new branch via merge request"
```

- [ ] **Step 6: write failing test verifying deterministic branch naming does not collide across calls**

Append a test that two successive agent_edit calls on the same base branch produce two distinct branches and two distinct open merge requests.

```python
def test_agent_edit_produces_distinct_branches_on_repeated_calls(db_session):
    artifact_id = "artifact-agent-2"
    artifact = DagVersionedArtifact(db_session, artifact_id, _paragraph_tokenizer)
    root = artifact.commit("Intro paragraph.\n\nBody paragraph.", "user-1", "root commit", None)
    artifact.branch("main", root)

    mr_id_one = agent_edit(
        db_session, artifact_id, "main", "First instruction.", _fake_llm_call
    )
    mr_id_two = agent_edit(
        db_session, artifact_id, "main", "Second instruction.", _fake_llm_call
    )

    mr_one = db_session.get(MergeRequest, mr_id_one)
    mr_two = db_session.get(MergeRequest, mr_id_two)

    assert mr_one.source_branch != mr_two.source_branch
    assert mr_one.status == "open"
    assert mr_two.status == "open"
```

- [ ] **Step 7: run test and confirm it fails**

Run this test in isolation first against a stub that always returns the same suffix to demonstrate the failure mode, then run the real test:

```bash
pytest backend/tests/collab/test_agent_editor.py::test_agent_edit_produces_distinct_branches_on_repeated_calls -v
```

Expected failure output, if branch names were not randomized, would be:

```
sqlalchemy.exc.IntegrityError: duplicate key value violates unique constraint on branch name
```

Given the Step 3 implementation already uses uuid4 hex suffixes, actually running the command above at this point produces:

```
1 passed
```

confirming that no regression exists; proceed to record this as a passing regression test rather than a fix.

- [ ] **Step 8: no further implementation change required**

Since the existing implementation from Step 3 already generates a fresh uuid4-derived suffix per call, no production code edit is needed here.

```python
# no code change needed, existing agent_edit implementation from Step 3
# already calls uuid.uuid4().hex[:8] independently on every invocation
```

- [ ] **Step 9: run full test file and confirm both tests pass**

Run:

```bash
pytest backend/tests/collab/test_agent_editor.py -v
```

Expected output: `2 passed`

- [ ] **Step 10: commit**

```bash
git add backend/tests/collab/test_agent_editor.py
git commit -m "Add regression test for distinct agent branch names across repeated agent_edit calls"
```

### Task 22: Frontend API Client, Artifact List, and Workspace View

**Files:**
- Create: frontend/src/api/client.ts
- Create: frontend/src/components/ArtifactList.tsx
- Create: frontend/src/components/WorkspaceView.tsx
- Test: frontend/src/api/client.test.ts
- Test: frontend/src/components/ArtifactList.test.tsx
- Test: frontend/src/components/WorkspaceView.test.tsx

**Interfaces:**
- Consumes: the assumed backend REST contract only, not a function signature: `GET /api/workspaces/:id/artifacts` returning a JSON array shaped like `Artifact[]`, and `GET /api/artifacts/:id/diff?ref_a=...&ref_b=...` returning a JSON array shaped like `DiffToken[]`. Also consumes the existing Vite plus React plus TypeScript scaffold with Vitest and React Testing Library already configured in `frontend/`.
- Produces:
  - `export interface Artifact { id: string; workspaceId: string; type: string; name: string; }`
  - `export interface DiffToken { kind: "unchanged" | "added" | "removed" | "changed"; text: string; oldText?: string; wordDiff?: DiffToken[]; }`
  - `export async function fetchArtifacts(workspaceId: string): Promise<Artifact[]>`
  - `export async function fetchDiff(artifactId: string, refA: string, refB: string): Promise<DiffToken[]>`
  - `export function ArtifactList({ artifacts, onSelect }: { artifacts: Artifact[]; onSelect: (id: string) => void }): JSX.Element`
  - `export function WorkspaceView({ workspaceId }: { workspaceId: string }): JSX.Element`

- [ ] **Step 1: Write a failing test for the API client functions**

Create `frontend/src/api/client.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchArtifacts, fetchDiff } from "./client";

describe("fetchArtifacts", () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  it("fetches artifacts for a workspace and parses JSON", async () => {
    const mockArtifacts = [
      { id: "artifact-1", workspaceId: "workspace-1", type: "doc", name: "Notes.md" },
    ];
    (global.fetch as any).mockResolvedValue({
      json: async () => mockArtifacts,
    });

    const result = await fetchArtifacts("workspace-1");

    expect(global.fetch).toHaveBeenCalledWith("/api/workspaces/workspace-1/artifacts");
    expect(result).toEqual(mockArtifacts);
  });
});

describe("fetchDiff", () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  it("fetches diff tokens with ref_a and ref_b query parameters", async () => {
    const mockTokens = [{ kind: "unchanged", text: "hello" }];
    (global.fetch as any).mockResolvedValue({
      json: async () => mockTokens,
    });

    const result = await fetchDiff("artifact-1", "main", "feature-1");

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/artifacts/artifact-1/diff?ref_a=main&ref_b=feature-1"
    );
    expect(result).toEqual(mockTokens);
  });
});
```

- [ ] **Step 2: Run the client test and confirm it fails**

Command: `cd frontend && npx vitest run src/api/client.test.ts`

Expected failure text: `Failed to resolve import "./client" from "src/api/client.test.ts". Does the file exist?`

- [ ] **Step 3: Implement the API client**

Create `frontend/src/api/client.ts`:

```ts
export interface Artifact {
  id: string;
  workspaceId: string;
  type: string;
  name: string;
}

export interface DiffToken {
  kind: "unchanged" | "added" | "removed" | "changed";
  text: string;
  oldText?: string;
  wordDiff?: DiffToken[];
}

export async function fetchArtifacts(workspaceId: string): Promise<Artifact[]> {
  const response = await fetch(`/api/workspaces/${workspaceId}/artifacts`);
  return response.json();
}

export async function fetchDiff(
  artifactId: string,
  refA: string,
  refB: string
): Promise<DiffToken[]> {
  const params = new URLSearchParams({ ref_a: refA, ref_b: refB });
  const response = await fetch(`/api/artifacts/${artifactId}/diff?${params.toString()}`);
  return response.json();
}
```

- [ ] **Step 4: Run the client test and confirm it passes**

Command: `cd frontend && npx vitest run src/api/client.test.ts`

Expected output: both tests pass, for example `Test Files 1 passed (1)` and `Tests 2 passed (2)`.

- [ ] **Step 5: Commit the API client**

```bash
cd frontend && git add src/api/client.ts src/api/client.test.ts && git commit -m "Add typed API client for artifacts and diff endpoints"
```

- [ ] **Step 6: Write a failing test for ArtifactList**

Create `frontend/src/components/ArtifactList.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ArtifactList } from "./ArtifactList";
import type { Artifact } from "../api/client";

describe("ArtifactList", () => {
  const artifacts: Artifact[] = [
    { id: "artifact-1", workspaceId: "workspace-1", type: "doc", name: "Notes.md" },
    { id: "artifact-2", workspaceId: "workspace-1", type: "chat", name: "Chat Export.json" },
  ];

  it("renders one list item per artifact", () => {
    render(<ArtifactList artifacts={artifacts} onSelect={() => {}} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("Notes.md")).toBeInTheDocument();
    expect(screen.getByText("Chat Export.json")).toBeInTheDocument();
  });

  it("calls onSelect with the clicked artifact id", () => {
    const onSelect = vi.fn();
    render(<ArtifactList artifacts={artifacts} onSelect={onSelect} />);
    fireEvent.click(screen.getByText("Chat Export.json"));
    expect(onSelect).toHaveBeenCalledWith("artifact-2");
  });
});
```

- [ ] **Step 7: Run the ArtifactList test and confirm it fails**

Command: `cd frontend && npx vitest run src/components/ArtifactList.test.tsx`

Expected failure text: `Failed to resolve import "./ArtifactList" from "src/components/ArtifactList.test.tsx". Does the file exist?`

- [ ] **Step 8: Implement ArtifactList**

Create `frontend/src/components/ArtifactList.tsx`:

```tsx
import type { Artifact } from "../api/client";

export interface ArtifactListProps {
  artifacts: Artifact[];
  onSelect: (id: string) => void;
}

export function ArtifactList({ artifacts, onSelect }: ArtifactListProps) {
  return (
    <ul className="artifact-list">
      {artifacts.map((artifact) => (
        <li key={artifact.id}>
          <button type="button" onClick={() => onSelect(artifact.id)}>
            {artifact.name}
          </button>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 9: Run the ArtifactList test and confirm it passes**

Command: `cd frontend && npx vitest run src/components/ArtifactList.test.tsx`

Expected output: both tests pass, for example `Tests 2 passed (2)`.

- [ ] **Step 10: Commit ArtifactList**

```bash
cd frontend && git add src/components/ArtifactList.tsx src/components/ArtifactList.test.tsx && git commit -m "Add ArtifactList component rendering clickable artifact names"
```

- [ ] **Step 11: Write a failing test for WorkspaceView**

Create `frontend/src/components/WorkspaceView.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { WorkspaceView } from "./WorkspaceView";
import * as client from "../api/client";

describe("WorkspaceView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders artifact names after fetchArtifacts resolves", async () => {
    vi.spyOn(client, "fetchArtifacts").mockResolvedValue([
      { id: "artifact-1", workspaceId: "workspace-1", type: "doc", name: "Notes.md" },
      { id: "artifact-2", workspaceId: "workspace-1", type: "code", name: "main.py" },
    ]);

    render(<WorkspaceView workspaceId="workspace-1" />);

    await waitFor(() => {
      expect(screen.getByText("Notes.md")).toBeInTheDocument();
    });
    expect(screen.getByText("main.py")).toBeInTheDocument();
    expect(client.fetchArtifacts).toHaveBeenCalledWith("workspace-1");
  });
});
```

- [ ] **Step 12: Run the WorkspaceView test and confirm it fails**

Command: `cd frontend && npx vitest run src/components/WorkspaceView.test.tsx`

Expected failure text: `Failed to resolve import "./WorkspaceView" from "src/components/WorkspaceView.test.tsx". Does the file exist?`

- [ ] **Step 13: Implement WorkspaceView**

Create `frontend/src/components/WorkspaceView.tsx`:

```tsx
import { useEffect, useState } from "react";
import { fetchArtifacts, type Artifact } from "../api/client";
import { ArtifactList } from "./ArtifactList";

export interface WorkspaceViewProps {
  workspaceId: string;
}

export function WorkspaceView({ workspaceId }: WorkspaceViewProps) {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;
    fetchArtifacts(workspaceId).then((result) => {
      if (isCurrent) {
        setArtifacts(result);
      }
    });
    return () => {
      isCurrent = false;
    };
  }, [workspaceId]);

  return (
    <div className="workspace-view">
      <ArtifactList artifacts={artifacts} onSelect={setSelectedId} />
      {selectedId !== null && (
        <p data-testid="selected-artifact-id">{selectedId}</p>
      )}
    </div>
  );
}
```

- [ ] **Step 14: Run the WorkspaceView test and confirm it passes**

Command: `cd frontend && npx vitest run src/components/WorkspaceView.test.tsx`

Expected output: the test passes, for example `Tests 1 passed (1)`.

- [ ] **Step 15: Commit WorkspaceView**

```bash
cd frontend && git add src/components/WorkspaceView.tsx src/components/WorkspaceView.test.tsx && git commit -m "Add WorkspaceView loading artifacts on mount and tracking selection"
```

### Task 23: Diff View Component

**Files:**
- Create: frontend/src/components/DiffView.tsx
- Test: frontend/src/components/DiffView.test.tsx

**Interfaces:**
- Consumes: `export interface DiffToken { kind: "unchanged" | "added" | "removed" | "changed"; text: string; oldText?: string; wordDiff?: DiffToken[]; }` from `frontend/src/api/client.ts` (Task 22).
- Produces: `export function DiffView({ tokens }: { tokens: DiffToken[] }): JSX.Element`, for a later task that fetches diff tokens with `fetchDiff` and renders them on an artifact diff page.

- [ ] **Step 1: Write a failing test covering all four token kinds plus a nested word diff**

Create `frontend/src/components/DiffView.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DiffView } from "./DiffView";
import type { DiffToken } from "../api/client";

describe("DiffView", () => {
  it("renders each diff token kind with the expected data-testid, including nested word diffs", () => {
    const tokens: DiffToken[] = [
      { kind: "unchanged", text: "The quick fox" },
      { kind: "added", text: "jumps over the fence" },
      { kind: "removed", text: "walked past the fence" },
      {
        kind: "changed",
        text: "the lazy dog",
        oldText: "the sleepy dog",
        wordDiff: [
          { kind: "unchanged", text: "the " },
          { kind: "removed", text: "sleepy" },
          { kind: "added", text: "lazy" },
          { kind: "unchanged", text: " dog" },
        ],
      },
    ];

    render(<DiffView tokens={tokens} />);

    expect(screen.getByTestId("diff-unchanged")).toHaveTextContent("The quick fox");
    expect(screen.getByTestId("diff-added")).toHaveTextContent("jumps over the fence");
    expect(screen.getByTestId("diff-removed")).toHaveTextContent("walked past the fence");
    expect(screen.getByTestId("diff-changed")).toBeInTheDocument();
    expect(screen.getByTestId("diff-word-removed")).toHaveTextContent("sleepy");
    expect(screen.getByTestId("diff-word-added")).toHaveTextContent("lazy");
  });
});
```

- [ ] **Step 2: Run the DiffView test and confirm it fails**

Command: `cd frontend && npx vitest run src/components/DiffView.test.tsx`

Expected failure text: `Failed to resolve import "./DiffView" from "src/components/DiffView.test.tsx". Does the file exist?`

- [ ] **Step 3: Implement DiffView**

Create `frontend/src/components/DiffView.tsx`:

```tsx
import type { CSSProperties } from "react";
import type { DiffToken } from "../api/client";

const KIND_STYLES: Record<DiffToken["kind"], CSSProperties> = {
  unchanged: {},
  added: { backgroundColor: "#d4f8d4" },
  removed: { backgroundColor: "#f8d4d4", textDecoration: "line-through" },
  changed: { backgroundColor: "#fff3b0" },
};

export interface DiffViewProps {
  tokens: DiffToken[];
}

function WordDiff({ wordDiff }: { wordDiff: DiffToken[] }) {
  return (
    <span className="diff-word-diff">
      {wordDiff.map((word, index) => (
        <span
          key={index}
          data-testid={`diff-word-${word.kind}`}
          className={`diff-token diff-${word.kind}`}
          style={KIND_STYLES[word.kind]}
        >
          {word.text}
        </span>
      ))}
    </span>
  );
}

function DiffTokenItem({ token }: { token: DiffToken }) {
  if (token.kind === "changed" && token.wordDiff && token.wordDiff.length > 0) {
    return (
      <span
        data-testid="diff-changed"
        className="diff-token diff-changed"
        style={KIND_STYLES.changed}
      >
        <WordDiff wordDiff={token.wordDiff} />
      </span>
    );
  }

  return (
    <span
      data-testid={`diff-${token.kind}`}
      className={`diff-token diff-${token.kind}`}
      style={KIND_STYLES[token.kind]}
    >
      {token.text}
    </span>
  );
}

export function DiffView({ tokens }: DiffViewProps) {
  return (
    <div className="diff-view">
      {tokens.map((token, index) => (
        <DiffTokenItem key={index} token={token} />
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run the DiffView test and confirm it passes**

Command: `cd frontend && npx vitest run src/components/DiffView.test.tsx`

Expected output: the test passes, for example `Tests 1 passed (1)`.

- [ ] **Step 5: Commit DiffView**

```bash
cd frontend && git add src/components/DiffView.tsx src/components/DiffView.test.tsx && git commit -m "Add DiffView rendering token kinds with nested word-level diffs"
```

### Task 24: Conflict Resolution UI

**Files:**
- Modify: frontend/src/api/client.ts
- Create: frontend/src/components/ConflictResolutionView.tsx
- Test: frontend/src/api/client.test.ts
- Test: frontend/src/components/ConflictResolutionView.test.tsx

**Interfaces:**
- Consumes: frontend/src/api/client.ts already exports `interface DiffToken` with fields `kind`, `text`, an optional `oldText`, and an optional `wordDiff`, added by an earlier task. This task does not change `DiffToken`; it appends new exports to the same file.
- Produces:
  - `export interface ConflictRecord { position: number; base?: string; ours?: string; theirs?: string; }`
  - `export async function fetchMergeRequest(mrId: string): Promise<{ conflicts: ConflictRecord[] }>`
  - `export async function submitResolution(mrId: string, resolutions: Record<number, string>): Promise<void>`
  - `export function ConflictResolutionView({ conflicts, onResolve }: { conflicts: ConflictRecord[]; onResolve: (resolutions: Record<number, string>) => void }): JSX.Element`

- [ ] **Step 1: Write a failing test for fetchMergeRequest and submitResolution**

Create `frontend/src/api/client.test.ts` with the following content:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchMergeRequest, submitResolution } from "./client";
import type { ConflictRecord } from "./client";

describe("fetchMergeRequest", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches conflicts for a merge request", async () => {
    const mockConflicts: ConflictRecord[] = [
      { position: 0, base: "base text", ours: "ours text", theirs: "theirs text" },
    ];
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ conflicts: mockConflicts }),
    }) as unknown as typeof fetch;

    const result = await fetchMergeRequest("mr-1");

    expect(global.fetch).toHaveBeenCalledWith("/api/merge-requests/mr-1/diff");
    expect(result.conflicts).toEqual(mockConflicts);
  });
});

describe("submitResolution", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("posts resolutions as JSON to the merge endpoint", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true }) as unknown as typeof fetch;

    await submitResolution("mr-1", { 0: "resolved text" });

    expect(global.fetch).toHaveBeenCalledWith("/api/merge-requests/mr-1/merge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resolutions: { 0: "resolved text" } }),
    });
  });
});
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
cd frontend && npx vitest run src/api/client.test.ts
```

Expected failure: the test run fails during module evaluation with an error stating `The requested module './client' does not provide an export named 'fetchMergeRequest'`, because `client.ts` does not yet export `fetchMergeRequest`, `submitResolution`, or `ConflictRecord`.

- [ ] **Step 3: Add ConflictRecord, fetchMergeRequest, and submitResolution to client.ts**

Append the following to `frontend/src/api/client.ts` (leaving the existing `DiffToken` interface and any other existing exports untouched):

```typescript
export interface ConflictRecord {
  position: number;
  base?: string;
  ours?: string;
  theirs?: string;
}

export async function fetchMergeRequest(mrId: string): Promise<{ conflicts: ConflictRecord[] }> {
  const response = await fetch(`/api/merge-requests/${mrId}/diff`);
  if (!response.ok) {
    throw new Error(`fetchMergeRequest failed with status ${response.status}`);
  }
  return response.json();
}

export async function submitResolution(
  mrId: string,
  resolutions: Record<number, string>
): Promise<void> {
  const response = await fetch(`/api/merge-requests/${mrId}/merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resolutions }),
  });
  if (!response.ok) {
    throw new Error(`submitResolution failed with status ${response.status}`);
  }
}
```

- [ ] **Step 4: Run the test again and confirm it passes**

Run:

```bash
cd frontend && npx vitest run src/api/client.test.ts
```

Expected: both tests in the `fetchMergeRequest` and `submitResolution` suites report as passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "Add merge request conflict fetch and resolution submission to API client"
```

- [ ] **Step 6: Write a failing test for ConflictResolutionView**

Create `frontend/src/components/ConflictResolutionView.test.tsx` with the following content:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConflictResolutionView } from "./ConflictResolutionView";
import type { ConflictRecord } from "../api/client";

describe("ConflictResolutionView", () => {
  it("submits the full resolution map once every conflict is resolved", () => {
    const conflicts: ConflictRecord[] = [
      { position: 0, base: "base 0", ours: "ours 0", theirs: "theirs 0" },
      { position: 1, base: "base 1", ours: "ours 1", theirs: "theirs 1" },
    ];
    const onResolve = vi.fn();

    render(<ConflictResolutionView conflicts={conflicts} onResolve={onResolve} />);

    const submitButton = screen.getByRole("button", { name: "Submit Merge" });
    expect(submitButton).toBeDisabled();

    const oursButtons = screen.getAllByRole("button", { name: "Use Ours" });
    fireEvent.click(oursButtons[0]);

    const customTextarea = screen.getByLabelText("custom-resolution-1");
    fireEvent.change(customTextarea, { target: { value: "custom text for conflict 1" } });
    const customButtons = screen.getAllByRole("button", { name: "Use Custom" });
    fireEvent.click(customButtons[1]);

    expect(submitButton).not.toBeDisabled();
    fireEvent.click(submitButton);

    expect(onResolve).toHaveBeenCalledWith({
      0: "ours 0",
      1: "custom text for conflict 1",
    });
  });
});
```

- [ ] **Step 7: Run the test and confirm it fails**

Run:

```bash
cd frontend && npx vitest run src/components/ConflictResolutionView.test.tsx
```

Expected failure: the test run fails with an error stating `Failed to resolve import "./ConflictResolutionView" from "src/components/ConflictResolutionView.test.tsx". Does the file exist?`, because the component file does not exist yet.

- [ ] **Step 8: Write the ConflictResolutionView implementation**

Create `frontend/src/components/ConflictResolutionView.tsx` with the following content:

```typescript
import { useState } from "react";
import type { ConflictRecord } from "../api/client";

export interface ConflictResolutionViewProps {
  conflicts: ConflictRecord[];
  onResolve: (resolutions: Record<number, string>) => void;
}

export function ConflictResolutionView({ conflicts, onResolve }: ConflictResolutionViewProps) {
  const [resolutions, setResolutions] = useState<Record<number, string>>({});
  const [draftText, setDraftText] = useState<Record<number, string>>({});

  const chooseOurs = (conflict: ConflictRecord) => {
    setResolutions((prev) => ({ ...prev, [conflict.position]: conflict.ours ?? "" }));
  };

  const chooseTheirs = (conflict: ConflictRecord) => {
    setResolutions((prev) => ({ ...prev, [conflict.position]: conflict.theirs ?? "" }));
  };

  const chooseCustom = (position: number) => {
    setResolutions((prev) => ({ ...prev, [position]: draftText[position] ?? "" }));
  };

  const updateDraft = (position: number, text: string) => {
    setDraftText((prev) => ({ ...prev, [position]: text }));
  };

  const allResolved = conflicts.every(
    (conflict) => resolutions[conflict.position] !== undefined
  );

  const handleSubmit = () => {
    onResolve(resolutions);
  };

  return (
    <div>
      {conflicts.map((conflict) => (
        <div key={conflict.position} data-testid={`conflict-${conflict.position}`}>
          <div>
            <div>
              <h4>Base</h4>
              <pre>{conflict.base}</pre>
            </div>
            <div>
              <h4>Ours</h4>
              <pre>{conflict.ours}</pre>
            </div>
            <div>
              <h4>Theirs</h4>
              <pre>{conflict.theirs}</pre>
            </div>
          </div>
          <button type="button" onClick={() => chooseOurs(conflict)}>
            Use Ours
          </button>
          <button type="button" onClick={() => chooseTheirs(conflict)}>
            Use Theirs
          </button>
          <textarea
            aria-label={`custom-resolution-${conflict.position}`}
            value={draftText[conflict.position] ?? ""}
            onChange={(event) => updateDraft(conflict.position, event.target.value)}
          />
          <button type="button" onClick={() => chooseCustom(conflict.position)}>
            Use Custom
          </button>
          {resolutions[conflict.position] !== undefined && (
            <p data-testid={`resolved-${conflict.position}`}>
              Resolved: {resolutions[conflict.position]}
            </p>
          )}
        </div>
      ))}
      <button type="button" onClick={handleSubmit} disabled={!allResolved}>
        Submit Merge
      </button>
    </div>
  );
}
```

- [ ] **Step 9: Run the test again and confirm it passes**

Run:

```bash
cd frontend && npx vitest run src/components/ConflictResolutionView.test.tsx
```

Expected: the test reports as passed, confirming `onResolve` was called with `{ 0: "ours 0", 1: "custom text for conflict 1" }`.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/ConflictResolutionView.tsx frontend/src/components/ConflictResolutionView.test.tsx
git commit -m "Add ConflictResolutionView for resolving merge conflicts"
```

### Task 25: Live Co-editor and Presence Indicator

**Files:**
- Create: frontend/src/components/LiveEditor.tsx
- Create: frontend/src/components/PresenceIndicator.tsx
- Test: frontend/src/components/LiveEditor.test.tsx
- Test: frontend/src/components/PresenceIndicator.test.tsx

**Interfaces:**
- Consumes: the `yjs` package (`Y.Doc`, `Y.Text`) and the `y-websocket` package (`WebsocketProvider`), both external npm dependencies rather than artifacts produced by earlier tasks in this plan.
- Produces:
  - `export interface LiveEditorProps { roomId: string; wsUrl: string; onReady?: (ydoc: Y.Doc, provider: WebsocketProvider) => void; }`
  - `export function LiveEditor(props: LiveEditorProps): JSX.Element`
  - `export interface PresenceIndicatorProps { provider: WebsocketProvider; }`
  - `export function PresenceIndicator(props: PresenceIndicatorProps): JSX.Element`

- [ ] **Step 1: Install yjs and y-websocket, then write a failing test for LiveEditor**

Run:

```bash
cd frontend && npm install yjs y-websocket
```

Create `frontend/src/components/LiveEditor.test.tsx` with the following content:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { LiveEditor } from "./LiveEditor";

vi.mock("y-websocket", () => {
  return {
    WebsocketProvider: vi.fn().mockImplementation(() => ({
      awareness: {
        getStates: () => new Map(),
        on: vi.fn(),
        off: vi.fn(),
      },
      destroy: vi.fn(),
    })),
  };
});

describe("LiveEditor", () => {
  it("renders a textarea and does not throw on mount or unmount", () => {
    expect(() => {
      const { unmount } = render(<LiveEditor roomId="room-1" wsUrl="ws://localhost:1234" />);
      expect(screen.getByRole("textbox")).toBeTruthy();
      unmount();
    }).not.toThrow();
  });
});
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
cd frontend && npx vitest run src/components/LiveEditor.test.tsx
```

Expected failure: the test run fails with an error stating `Failed to resolve import "./LiveEditor" from "src/components/LiveEditor.test.tsx". Does the file exist?`, because the component file does not exist yet.

- [ ] **Step 3: Write the LiveEditor implementation**

Create `frontend/src/components/LiveEditor.tsx` with the following content:

```typescript
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";

export interface LiveEditorProps {
  roomId: string;
  wsUrl: string;
  onReady?: (ydoc: Y.Doc, provider: WebsocketProvider) => void;
}

export function LiveEditor({ roomId, wsUrl, onReady }: LiveEditorProps) {
  const [text, setText] = useState("");
  const ydocRef = useRef<Y.Doc | null>(null);
  const ytextRef = useRef<Y.Text | null>(null);

  useEffect(() => {
    const ydoc = new Y.Doc();
    const provider = new WebsocketProvider(wsUrl, roomId, ydoc);
    const ytext = ydoc.getText("content");

    ydocRef.current = ydoc;
    ytextRef.current = ytext;
    setText(ytext.toString());

    const handleUpdate = () => {
      setText(ytext.toString());
    };
    ytext.observe(handleUpdate);

    if (onReady) {
      onReady(ydoc, provider);
    }

    return () => {
      ytext.unobserve(handleUpdate);
      provider.destroy();
      ydoc.destroy();
    };
  }, [roomId, wsUrl, onReady]);

  const handleChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = event.target.value;
    const ytext = ytextRef.current;
    const ydoc = ydocRef.current;
    if (!ytext || !ydoc) {
      return;
    }
    ydoc.transact(() => {
      ytext.delete(0, ytext.length);
      ytext.insert(0, newValue);
    });
  };

  return <textarea value={text} onChange={handleChange} aria-label="live-editor" />;
}
```

- [ ] **Step 4: Run the test again and confirm it passes**

Run:

```bash
cd frontend && npx vitest run src/components/LiveEditor.test.tsx
```

Expected: the test reports as passed, confirming a textarea renders and neither mount nor unmount throws.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/LiveEditor.tsx frontend/src/components/LiveEditor.test.tsx frontend/package.json frontend/package-lock.json
git commit -m "Add LiveEditor CRDT-backed collaborative textarea"
```

- [ ] **Step 6: Write a failing test for PresenceIndicator**

Create `frontend/src/components/PresenceIndicator.test.tsx` with the following content:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PresenceIndicator } from "./PresenceIndicator";
import type { WebsocketProvider } from "y-websocket";

describe("PresenceIndicator", () => {
  it("renders a presence dot and label for each connected user", () => {
    const fakeStates = new Map([
      [1, { user: { name: "Alice", color: "#ff0000" } }],
      [2, { user: { name: "Bob", color: "#00ff00" } }],
    ]);
    const fakeAwareness = {
      getStates: () => fakeStates,
      on: () => {},
    };
    const fakeProvider = { awareness: fakeAwareness } as unknown as WebsocketProvider;

    render(<PresenceIndicator provider={fakeProvider} />);

    expect(screen.getByText("Alice")).toBeTruthy();
    expect(screen.getByText("Bob")).toBeTruthy();
    expect(screen.getByTestId("presence-dot-1")).toBeTruthy();
    expect(screen.getByTestId("presence-dot-2")).toBeTruthy();
  });
});
```

- [ ] **Step 7: Run the test and confirm it fails**

Run:

```bash
cd frontend && npx vitest run src/components/PresenceIndicator.test.tsx
```

Expected failure: the test run fails with an error stating `Failed to resolve import "./PresenceIndicator" from "src/components/PresenceIndicator.test.tsx". Does the file exist?`, because the component file does not exist yet.

- [ ] **Step 8: Write the PresenceIndicator implementation**

Create `frontend/src/components/PresenceIndicator.tsx` with the following content:

```typescript
import { useEffect, useState } from "react";
import type { WebsocketProvider } from "y-websocket";

export interface PresenceIndicatorProps {
  provider: WebsocketProvider;
}

interface AwarenessUser {
  name: string;
  color: string;
}

export function PresenceIndicator({ provider }: PresenceIndicatorProps) {
  const [users, setUsers] = useState<Array<{ clientId: number; user: AwarenessUser }>>([]);

  useEffect(() => {
    const awareness = provider.awareness;

    const readStates = () => {
      const states = awareness.getStates() as Map<number, { user?: AwarenessUser }>;
      const nextUsers: Array<{ clientId: number; user: AwarenessUser }> = [];
      states.forEach((state, clientId) => {
        if (state.user) {
          nextUsers.push({ clientId, user: state.user });
        }
      });
      setUsers(nextUsers);
    };

    readStates();
    awareness.on("change", readStates);

    return () => {
      if (typeof awareness.off === "function") {
        awareness.off("change", readStates);
      }
    };
  }, [provider]);

  return (
    <div aria-label="presence-indicator">
      {users.map(({ clientId, user }) => (
        <div key={clientId} data-testid={`presence-dot-${clientId}`}>
          <span
            data-testid={`dot-color-${clientId}`}
            style={{
              backgroundColor: user.color,
              borderRadius: "50%",
              display: "inline-block",
              width: "10px",
              height: "10px",
            }}
          />
          <span>{user.name}</span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 9: Run the test again and confirm it passes**

Run:

```bash
cd frontend && npx vitest run src/components/PresenceIndicator.test.tsx
```

Expected: the test reports as passed, confirming two presence dots render with labels `Alice` and `Bob`.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/PresenceIndicator.tsx frontend/src/components/PresenceIndicator.test.tsx
git commit -m "Add PresenceIndicator showing connected collaborators"
```

### Task 26: Frontend Search and Chat Panel

**Files:**
- Create: frontend/src/components/SearchChatPanel.tsx
- Test: frontend/src/components/SearchChatPanel.test.tsx

**Interfaces:**
- Consumes: frontend/src/api/client.ts (existing file, to be extended in this task)
- Produces: `interface SearchResult { chunkId: string; text: string; artifactId: string; commitRef: string; score: number; }` and `searchQuery(q: string): Promise<SearchResult[]>` exported from frontend/src/api/client.ts; `SearchChatPanel` React component exported from frontend/src/components/SearchChatPanel.tsx

- [ ] **Step 1: write a failing test for searchQuery in the api client**

Create frontend/src/api/client.test.ts (or append to an existing test file at that path if one already exists) with the following content:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { searchQuery } from './client';

describe('searchQuery', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  it('fetches GET /api/search with the q parameter url encoded and maps the response', async () => {
    const mockResponse = [
      {
        chunk_id: 'chunk-1',
        text: 'the mitochondria is the powerhouse of the cell',
        artifact_id: 'artifact-1',
        commit_ref: 'commit-abc',
        score: 0.87,
      },
    ];
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const results = await searchQuery('mitochondria function');

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/search?q=mitochondria%20function')
    );
    expect(results).toEqual([
      {
        chunkId: 'chunk-1',
        text: 'the mitochondria is the powerhouse of the cell',
        artifactId: 'artifact-1',
        commitRef: 'commit-abc',
        score: 0.87,
      },
    ]);
  });
});
```

- [ ] **Step 2: run the test and confirm it fails**

Run:

```bash
npx vitest run frontend/src/api/client.test.ts
```

Expected failure output (searchQuery does not exist yet):

```
FAIL  frontend/src/api/client.test.ts
  Error: [vitest] No "searchQuery" export is defined on the "./client" mock or the module itself.
  SyntaxError / TypeError: searchQuery is not a function
```

- [ ] **Step 3: implement SearchResult and searchQuery in the api client**

Open frontend/src/api/client.ts and add the following to the end of the file:

```typescript
export interface SearchResult {
  chunkId: string;
  text: string;
  artifactId: string;
  commitRef: string;
  score: number;
}

interface RawSearchResult {
  chunk_id: string;
  text: string;
  artifact_id: string;
  commit_ref: string;
  score: number;
}

export async function searchQuery(q: string): Promise<SearchResult[]> {
  const encoded = encodeURIComponent(q);
  const response = await fetch(`${API_BASE_URL}/api/search?q=${encoded}`);
  if (!response.ok) {
    throw new Error(`search request failed with status ${response.status}`);
  }
  const raw: RawSearchResult[] = await response.json();
  return raw.map((r) => ({
    chunkId: r.chunk_id,
    text: r.text,
    artifactId: r.artifact_id,
    commitRef: r.commit_ref,
    score: r.score,
  }));
}
```

Note: `API_BASE_URL` is assumed to already exist as an exported or module-level constant in frontend/src/api/client.ts from an earlier task, pointing at the backend base URL (for example via `import.meta.env.VITE_API_URL`). If no such constant exists yet in the file, add this line near the top of the file before using it:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL ?? '';
```

- [ ] **Step 4: run the test again and confirm it passes**

Run:

```bash
npx vitest run frontend/src/api/client.test.ts
```

Expected output:

```
PASS  frontend/src/api/client.test.ts
  searchQuery
    ✓ fetches GET /api/search with the q parameter url encoded and maps the response
```

- [ ] **Step 5: commit the api client changes**

```bash
git add frontend/src/api/client.ts frontend/src/api/client.test.ts
git commit -m "Add searchQuery and SearchResult to frontend api client"
```

- [ ] **Step 6: write a failing test for the SearchChatPanel component**

Create frontend/src/components/SearchChatPanel.test.tsx with the following content:

```typescript
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SearchChatPanel } from './SearchChatPanel';
import * as client from '../api/client';

describe('SearchChatPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders mocked results with visible provenance labels after a submitted query', async () => {
    vi.spyOn(client, 'searchQuery').mockResolvedValue([
      {
        chunkId: 'chunk-1',
        text: 'the mitochondria is the powerhouse of the cell',
        artifactId: 'artifact-1',
        commitRef: 'commit-abc',
        score: 0.87,
      },
      {
        chunkId: 'chunk-2',
        text: 'ribosomes synthesize proteins from amino acids',
        artifactId: 'artifact-2',
        commitRef: 'commit-def',
        score: 0.65,
      },
    ]);

    render(<SearchChatPanel />);

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'cell biology' } });

    const button = screen.getByRole('button', { name: /search/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/the mitochondria is the powerhouse of the cell/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/ribosomes synthesize proteins from amino acids/i)).toBeInTheDocument();
    expect(screen.getByText('artifact-1 @ commit-abc')).toBeInTheDocument();
    expect(screen.getByText('artifact-2 @ commit-def')).toBeInTheDocument();
    expect(client.searchQuery).toHaveBeenCalledWith('cell biology');
  });
});
```

- [ ] **Step 7: run the test and confirm it fails**

Run:

```bash
npx vitest run frontend/src/components/SearchChatPanel.test.tsx
```

Expected failure output (module does not exist yet):

```
FAIL  frontend/src/components/SearchChatPanel.test.tsx
  Error: Failed to resolve import "./SearchChatPanel" from "frontend/src/components/SearchChatPanel.test.tsx"
```

- [ ] **Step 8: implement the SearchChatPanel component**

Create frontend/src/components/SearchChatPanel.tsx with the following content:

```typescript
import React, { useState } from 'react';
import { searchQuery, SearchResult } from '../api/client';

export function SearchChatPanel() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const found = await searchQuery(query);
      setResults(found);
    } catch (err) {
      setError('search failed, please try again');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="search-chat-panel">
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="ask a question about your research"
        />
        <button type="submit" disabled={isLoading}>
          Search
        </button>
      </form>
      {error && <div className="search-error">{error}</div>}
      <ul className="search-results">
        {results.map((r) => (
          <li key={r.chunkId} className="search-result-item">
            <div className="search-result-text">{r.text}</div>
            <div className="search-result-provenance">
              {r.artifactId} @ {r.commitRef}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 9: run the test again and confirm it passes**

Run:

```bash
npx vitest run frontend/src/components/SearchChatPanel.test.tsx
```

Expected output:

```
PASS  frontend/src/components/SearchChatPanel.test.tsx
  SearchChatPanel
    ✓ renders mocked results with visible provenance labels after a submitted query
```

- [ ] **Step 10: commit the component**

```bash
git add frontend/src/components/SearchChatPanel.tsx frontend/src/components/SearchChatPanel.test.tsx
git commit -m "Add SearchChatPanel component for querying the search API"
```

### Task 27: Docker Compose Integration, End to End Smoke Test, and README

**Files:**
- Create: docker-compose.yml (finalized at repo root, extending the earlier skeleton)
- Create: scripts/e2e_smoke.py
- Create: README.md

**Interfaces:**
- Consumes: backend service exposing POST /api/artifacts/ingest/markdown, POST /api/artifacts/ingest/chatgpt, GET /api/search, branch/commit/merge-request/diff endpoints from earlier tasks; frontend service built from frontend/; crdt-relay Node service from an earlier task; postgres service with pgvector
- Produces: a runnable `docker compose up --build` stack and a manual smoke-test script scripts/e2e_smoke.py that exercises ingestion, branching and merge conflict detection, and search across the whole stack; README.md describing the project for hackathon judges

This task is documentation and configuration only. No test-first steps apply because docker-compose.yml, scripts/e2e_smoke.py, and README.md are not unit-testable in the pytest/vitest sense; instead each artifact is described in full below exactly as it would be written to disk.

The final root docker-compose.yml content:

```yaml
version: "3.9"

services:
  postgres:
    image: ankane/pgvector:v0.5.1
    container_name: gfr-postgres
    environment:
      POSTGRES_USER: gfr
      POSTGRES_PASSWORD: gfr
      POSTGRES_DB: gfr
    ports:
      - "5432:5432"
    volumes:
      - gfr-postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gfr -d gfr"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: gfr-backend
    environment:
      DATABASE_URL: postgresql+psycopg2://gfr:gfr@postgres:5432/gfr
      MOCK_USER_ID: user-1
      EMBEDDING_MODEL_NAME: sentence-transformers/all-MiniLM-L6-v2
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - gfr-artifact-store:/data/artifacts

  crdt-relay:
    build:
      context: ./crdt-relay
      dockerfile: Dockerfile
    container_name: gfr-crdt-relay
    environment:
      RELAY_PORT: "1234"
      BACKEND_URL: http://backend:8000
    ports:
      - "1234:1234"
    depends_on:
      - backend

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: gfr-frontend
    environment:
      VITE_API_URL: http://backend:8000
      VITE_CRDT_WS_URL: ws://crdt-relay:1234
    ports:
      - "5173:5173"
    depends_on:
      - backend
      - crdt-relay

volumes:
  gfr-postgres-data:
  gfr-artifact-store:
```

The full content of scripts/e2e_smoke.py:

```python
#!/usr/bin/env python3
"""
End to end smoke test for Git for Research.

This script requires `docker compose up --build` to already be running
against the root docker-compose.yml before it is executed. It is meant
to be run manually as the final integration check against a live stack,
not as part of the pytest suite, since it makes real HTTP calls across
service boundaries and depends on container networking and timing.

Usage:
    python scripts/e2e_smoke.py
"""

import sys
import tempfile
import os

import requests

BASE_URL = os.environ.get("GFR_BASE_URL", "http://localhost:8000")
USER_ID = "user-1"

CHATGPT_EXPORT_FIXTURE = """{
  "title": "Sample Research Chat",
  "mapping": {
    "node-1": {
      "message": {
        "author": {"role": "user"},
        "content": {"parts": ["What is the boiling point of water at sea level?"]}
      }
    },
    "node-2": {
      "message": {
        "author": {"role": "assistant"},
        "content": {"parts": ["Water boils at 100 degrees Celsius at sea level."]}
      }
    }
  }
}"""

MARKDOWN_FIXTURE = """# Research Notes

## Introduction

Mitochondria are membrane bound organelles found in most eukaryotic cells.

## Findings

The paragraph under study describes ATP production in the citric acid cycle.
"""


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def step(title: str) -> None:
    print(f"\n=== {title} ===")


def ingest_markdown() -> str:
    step("Step 1a: ingest markdown fixture")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(MARKDOWN_FIXTURE)
        path = f.name
    with open(path, "rb") as fh:
        response = requests.post(
            f"{BASE_URL}/api/artifacts/ingest/markdown",
            files={"file": ("research_notes.md", fh, "text/markdown")},
            data={"user_id": USER_ID},
        )
    os.remove(path)
    if response.status_code != 200:
        fail(f"markdown ingest returned status {response.status_code}: {response.text}")
    body = response.json()
    if "artifact_id" not in body:
        fail(f"markdown ingest response missing artifact_id: {body}")
    artifact_id = body["artifact_id"]
    print(f"ingested markdown artifact_id={artifact_id}")
    return artifact_id


def ingest_chatgpt() -> str:
    step("Step 1b: ingest chatgpt export fixture")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(CHATGPT_EXPORT_FIXTURE)
        path = f.name
    with open(path, "rb") as fh:
        response = requests.post(
            f"{BASE_URL}/api/artifacts/ingest/chatgpt",
            files={"file": ("chat_export.json", fh, "application/json")},
            data={"user_id": USER_ID},
        )
    os.remove(path)
    if response.status_code != 200:
        fail(f"chatgpt ingest returned status {response.status_code}: {response.text}")
    body = response.json()
    if "artifact_id" not in body:
        fail(f"chatgpt ingest response missing artifact_id: {body}")
    artifact_id = body["artifact_id"]
    print(f"ingested chatgpt artifact_id={artifact_id}")
    return artifact_id


def create_conflicting_branch_and_merge(markdown_artifact_id: str) -> None:
    step("Step 2a: create a branch on the markdown artifact")
    branch_response = requests.post(
        f"{BASE_URL}/api/artifacts/{markdown_artifact_id}/branches",
        json={"branch_name": "edit-atp-paragraph", "user_id": USER_ID},
    )
    if branch_response.status_code != 200:
        fail(f"branch creation returned status {branch_response.status_code}: {branch_response.text}")
    print("created branch edit-atp-paragraph")

    step("Step 2b: commit a conflicting edit on the branch")
    branch_commit_response = requests.post(
        f"{BASE_URL}/api/artifacts/{markdown_artifact_id}/commits",
        json={
            "branch_name": "edit-atp-paragraph",
            "user_id": USER_ID,
            "content": MARKDOWN_FIXTURE.replace(
                "The paragraph under study describes ATP production in the citric acid cycle.",
                "The paragraph under study describes ATP synthesis inside the mitochondrial matrix.",
            ),
            "message": "clarify ATP synthesis location on branch",
        },
    )
    if branch_commit_response.status_code != 200:
        fail(f"branch commit returned status {branch_commit_response.status_code}: {branch_commit_response.text}")
    print("committed conflicting edit on branch")

    step("Step 2c: commit a different conflicting edit on main covering the same paragraph")
    main_commit_response = requests.post(
        f"{BASE_URL}/api/artifacts/{markdown_artifact_id}/commits",
        json={
            "branch_name": "main",
            "user_id": USER_ID,
            "content": MARKDOWN_FIXTURE.replace(
                "The paragraph under study describes ATP production in the citric acid cycle.",
                "The paragraph under study describes ATP production during oxidative phosphorylation.",
            ),
            "message": "clarify ATP production mechanism on main",
        },
    )
    if main_commit_response.status_code != 200:
        fail(f"main commit returned status {main_commit_response.status_code}: {main_commit_response.text}")
    print("committed conflicting edit on main")

    step("Step 2d: open a merge request from the branch into main")
    merge_request_response = requests.post(
        f"{BASE_URL}/api/artifacts/{markdown_artifact_id}/merge-requests",
        json={
            "source_branch": "edit-atp-paragraph",
            "target_branch": "main",
            "user_id": USER_ID,
        },
    )
    if merge_request_response.status_code != 200:
        fail(f"merge request creation returned status {merge_request_response.status_code}: {merge_request_response.text}")
    merge_request_body = merge_request_response.json()
    if "merge_request_id" not in merge_request_body:
        fail(f"merge request response missing merge_request_id: {merge_request_body}")
    merge_request_id = merge_request_body["merge_request_id"]
    print(f"opened merge_request_id={merge_request_id}")

    step("Step 2e: assert the diff endpoint reports a conflict")
    diff_response = requests.get(
        f"{BASE_URL}/api/artifacts/{markdown_artifact_id}/merge-requests/{merge_request_id}/diff"
    )
    if diff_response.status_code != 200:
        fail(f"diff endpoint returned status {diff_response.status_code}: {diff_response.text}")
    diff_body = diff_response.json()
    if not diff_body.get("has_conflict", False):
        fail(f"expected diff endpoint to report has_conflict true, got: {diff_body}")
    print("diff endpoint correctly reported a conflict")


def run_search(expected_artifact_ids: list) -> None:
    step("Step 3: run a search query and assert an ingested artifact appears")
    search_response = requests.get(
        f"{BASE_URL}/api/search",
        params={"q": "mitochondria ATP production"},
    )
    if search_response.status_code != 200:
        fail(f"search endpoint returned status {search_response.status_code}: {search_response.text}")
    results = search_response.json()
    found_artifact_ids = {r.get("artifact_id") for r in results}
    if not found_artifact_ids.intersection(expected_artifact_ids):
        fail(
            "expected at least one ingested artifact id "
            f"{expected_artifact_ids} in search results, got artifact ids {found_artifact_ids}"
        )
    print(f"search returned {len(results)} results including an ingested artifact")


def main() -> None:
    print("Running Git for Research end to end smoke test against", BASE_URL)
    print("This script assumes docker compose up --build is already running.")

    markdown_artifact_id = ingest_markdown()
    chatgpt_artifact_id = ingest_chatgpt()

    create_conflicting_branch_and_merge(markdown_artifact_id)

    run_search([markdown_artifact_id, chatgpt_artifact_id])

    print("\nAll smoke test steps passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

The full content of README.md at the repo root:

```markdown
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
  exports, PDFs, codebases) are normalized into a common versioned object
  model backed by Postgres, with codebase artifacts additionally tracked
  through pygit2 and structurally parsed with tree-sitter.
- **Commit, diff, branch, and merge engine**: a git-like layer that produces
  commits and paragraph or chunk level diffs, supports branching per
  artifact, and detects merge conflicts when overlapping regions are edited
  independently on two branches.
- **CRDT-backed concurrent editing layer**: a Node.js y-websocket relay that
  lets multiple mock users edit the same artifact concurrently, with changes
  eventually reconciled into the commit history.
- **Ingestion pipeline**: endpoints that accept markdown documents, ChatGPT
  export JSON, PDFs, and codebases, normalize them into artifacts, and chunk
  them for downstream retrieval.
- **Retrieval and embeddings**: local sentence-transformers embeddings stored
  and queried through pgvector, with no external embedding API dependency.
- **Query and chat surface**: a FastAPI search endpoint returning ranked
  chunks with provenance (artifact id, commit ref, score), consumed by a
  React search panel; any LLM summarization step is an injected, mockable
  callable so the system runs fully offline in tests.
- **Frontend**: a React and TypeScript (Vite) application providing artifact
  views, diff views, branch and merge controls, and the search and chat
  panel described above.

## How to run it

```bash
docker compose up --build
```

Once all services report healthy (postgres, backend, crdt-relay, frontend),
run the end to end smoke test from a separate terminal:

```bash
python scripts/e2e_smoke.py
```

The frontend is served at http://localhost:5173, the backend API at
http://localhost:8000, and the CRDT relay at ws://localhost:1234.

## What was completed versus not

Mandatory pillars:

- [x] Versioned artifact model with commit, diff, branch, and merge across
      markdown docs, ChatGPT exports, PDFs, and codebases
- [x] CRDT-backed concurrent editing layer via a Node.js y-websocket relay
- [x] Local, offline embedding and retrieval pipeline using
      sentence-transformers and pgvector, with no external LLM dependency
- [x] Search and chat surface in the frontend backed by the retrieval API,
      with provenance shown on every result

Stretch goals:

- [ ] Tree-sitter driven structural diffing of codebase artifacts beyond
      line-level diffs
- [ ] Automatic conflict resolution suggestions surfaced in the merge UI
- [ ] Production-grade OCR support for scanned PDF artifacts

## What would be built next

With more time, the next priorities would be structural, tree-sitter aware
diffs for codebase artifacts so that merges reason about function and class
boundaries rather than raw lines, a conflict resolution assistant that
proposes candidate merged text for a human to accept or edit rather than
only flagging conflicts, authentication and per-user permissions to replace
the current mock user id scheme, and a more thorough PDF ingestion path that
handles scanned pages instead of assuming extractable text.
```

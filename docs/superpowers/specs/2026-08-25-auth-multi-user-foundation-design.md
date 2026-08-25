# Auth & multi-user foundation — design

## Why

Every "who did this" concept in Git for Research today — commit `author`,
`last_seen.user_id`, the frontend's hardcoded `'user-1'` — is a free-text
string the client supplies on each request. There is no `users` table and
nothing validates these strings against anything real. This is sub-project 1
of a larger roadmap (comments/discussion, tags/releases, activity feed,
issues, notifications, stars, forking); those all need at least one thing
this project provides: a real, validated user identity to attach to.

This is deliberately a **lightweight, local, passwordless** profile system —
this app runs on one machine for one person's research, not deployed
multi-tenant, so full session-based auth (cookies/JWT, password hashing) is
out of scope. If the app is ever deployed for real multi-user access over a
network, auth should be revisited then; this design does not attempt to be
forward-compatible with that.

## Data model

New table, `users`:

| column | type | notes |
|---|---|---|
| `id` | string (uuid), primary key | |
| `username` | string, unique | what gets stored in `commits.author` / `last_seen.user_id` |
| `display_name` | string | defaults to `username` if not given |
| `created_at` | datetime | |

No other schema changes in this phase. `commits.author` and
`last_seen.user_id` stay as plain strings — this project adds validation
that those strings correspond to a real `users.username`, not a schema
change to those tables. (A `merge_requests.created_by` column, and any
schema needed for comments/activity, is explicitly out of scope here — that
belongs to the next sub-project, so this stays a tight, single-purpose
foundation.)

## Backend

- `backend/app/users.py` — `create_user(session, username, display_name=None)`,
  `get_user_by_username(session, username)`, `list_users(session)`. Mirrors
  the existing style of `app/artifacts.py`.
- `backend/app/api/routes_users.py`:
  - `POST /api/users` — body `{username, display_name?}`. 409 if the
    username already exists (mirrors the existing duplicate-branch pattern
    in `dag_store.create_branch`).
  - `GET /api/users` — list all profiles, for the frontend's profile picker.
- A `require_user(db, username)` helper (in `app/api/deps.py`, alongside the
  existing `tokenizer_for_type`), raising 404 if the username doesn't exist.
  Wired into every endpoint that currently accepts a client-supplied
  `author`/`user_id`:
  - `POST /artifacts/{id}/commits` (`routes_versioning.py`) — validate
    `body.author`.
  - Ingestion routes (`routes_ingestion.py`) — these currently hardcode
    `"user-1"` in `_commit_and_index` and don't accept an author at all.
    They'll start accepting one (from the request) and validating it.
  - `POST /artifacts/{id}/seen` and `GET /artifacts/{id}/changes`
    (`routes_versioning.py`) — validate `user_id`.

No changes to `routes_collab.py` (merge requests, agent-edit) in this
phase — those don't currently track an actor at all, and adding that is
part of the next sub-project, not this one.

## Frontend

- `frontend/src/profile/ProfileContext.tsx` — same pattern as the existing
  `ThemeContext`: holds `{ username, displayName } | null`, persisted to
  `localStorage`, with `setProfile`/`clearProfile`.
- `frontend/src/components/ProfileGate.tsx` — shown once, before the rest of
  the app, if no profile is stored yet (or the stored one no longer exists
  server-side): lists existing profiles (fetched via `GET /api/users`) to
  pick from, plus a small "create new profile" form. Blocks rendering
  `LandingPage`/`WorkspaceApp` until resolved, the same way `ThemeProvider`
  wraps the app today.
- `frontend/src/components/ui/ProfileSwitcher.tsx` — small pill in the
  header next to `ThemeToggle`, showing the active profile's display name;
  clicking it re-opens the picker.
- Replace every hardcoded `'user-1'`:
  - `api.ts`: `createCommit`'s `author` default, `getChanges`/`markSeen`'s
    caller sites — drop the hardcoded defaults, callers now pass the real
    active profile.
  - `ChangesPanel.tsx`: `const USER_ID = 'user-1'` → `useProfile().username`.
  - `BranchesPanel.tsx`: commit form's implicit author → active profile.
  - `IngestPanel.tsx`: now sends the active profile's username as the
    ingestion author.

## Testing

- Backend (pytest, following this repo's existing conventions — real
  Postgres via `get_session()`/`TestClient`, not mocked):
  - `users.py`: create, get, list, duplicate-username conflict.
  - Route-level: unknown author/user_id on commit, ingestion, and
    mark-seen/changes endpoints returns 404; valid ones succeed.
- Frontend: no existing test suite to extend (Vitest is configured but
  empty). Verify manually via Playwright: create a profile, switch
  profiles, confirm a new commit and the "what changed" panel attribute to
  the correct username end to end.

## Error handling

- Duplicate `username` on create → 409 (matches the existing duplicate-
  branch pattern).
- Unknown `author`/`user_id` referenced on any write → 404 (matches the
  existing `_artifact_or_404` pattern in `routes_versioning.py`).
- No delete-profile endpoint in this phase, so "stored profile no longer
  exists server-side" can only happen if someone manually clears the
  database — the frontend handles it by falling back to `ProfileGate`.

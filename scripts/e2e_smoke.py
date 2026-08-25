#!/usr/bin/env python3
"""
End to end smoke test for Git for Research.

This script requires a running backend (either `docker compose up --build`
against the root docker-compose.yml, or a local `uvicorn app.main:app`
pointed at a reachable Postgres+pgvector instance) before it is executed.
It is meant to be run manually as an integration check against a live
stack, not as part of the pytest suite, since it makes real HTTP calls and
depends on a running server and database.

The FastAPI route layer (`backend/app/api/`) now exists and every request
below has been run by hand against a live server -- see README.md, "How to
run it".

Usage:
    python scripts/e2e_smoke.py
    (or, using the backend's virtualenv which already has `requests`:
     backend/.venv/bin/python scripts/e2e_smoke.py)
"""

import sys
import tempfile
import os
import uuid

import requests

BASE_URL = os.environ.get("GFR_BASE_URL", "http://localhost:8000")
USER_ID = f"smoke-test-{uuid.uuid4().hex[:8]}"
WORKSPACE_ID = str(uuid.uuid4())

CHATGPT_EXPORT_FIXTURE = """[
  {
    "title": "Sample Research Chat",
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
          "content": {"parts": ["What is the boiling point of water at sea level?"]},
          "create_time": 1000.0
        },
        "parent": "root",
        "children": ["n2"]
      },
      "n2": {
        "id": "n2",
        "message": {
          "author": {"role": "assistant"},
          "content": {"parts": ["Water boils at 100 degrees Celsius at sea level."]},
          "create_time": 1001.0
        },
        "parent": "n1",
        "children": []
      }
    }
  }
]"""

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


def create_user() -> None:
    step("Step 0: create the smoke-test user")
    response = requests.post(f"{BASE_URL}/api/users", json={"username": USER_ID})
    if response.status_code != 200:
        fail(f"user creation returned status {response.status_code}: {response.text}")
    print(f"created user username={USER_ID}")


def ingest_markdown() -> str:
    step("Step 1a: ingest markdown fixture")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(MARKDOWN_FIXTURE)
        path = f.name
    with open(path, "rb") as fh:
        response = requests.post(
            f"{BASE_URL}/api/workspaces/{WORKSPACE_ID}/artifacts/ingest/markdown",
            files={"file": ("research_notes.md", fh, "text/markdown")},
            data={"author": USER_ID},
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
            f"{BASE_URL}/api/workspaces/{WORKSPACE_ID}/artifacts/ingest/chatgpt",
            files={"file": ("chat_export.json", fh, "application/json")},
            data={"author": USER_ID},
        )
    os.remove(path)
    if response.status_code != 200:
        fail(f"chatgpt ingest returned status {response.status_code}: {response.text}")
    body = response.json()
    if "artifacts" not in body or not body["artifacts"]:
        fail(f"chatgpt ingest response missing artifacts: {body}")
    artifact_id = body["artifacts"][0]["artifact_id"]
    print(f"ingested chatgpt artifact_id={artifact_id}")
    return artifact_id


def create_conflicting_branch_and_merge(markdown_artifact_id: str) -> None:
    step("Step 2a: create a branch on the markdown artifact")
    branch_response = requests.post(
        f"{BASE_URL}/api/artifacts/{markdown_artifact_id}/branches",
        json={"name": "edit-atp-paragraph", "from_ref": "main"},
    )
    if branch_response.status_code != 200:
        fail(f"branch creation returned status {branch_response.status_code}: {branch_response.text}")
    print("created branch edit-atp-paragraph")

    step("Step 2b: commit a conflicting edit on the branch")
    branch_commit_response = requests.post(
        f"{BASE_URL}/api/artifacts/{markdown_artifact_id}/commits",
        json={
            "branch_name": "edit-atp-paragraph",
            "author": USER_ID,
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
            "author": USER_ID,
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
        json={"source_branch": "edit-atp-paragraph", "target_branch": "main", "author": USER_ID},
    )
    if merge_request_response.status_code != 200:
        fail(f"merge request creation returned status {merge_request_response.status_code}: {merge_request_response.text}")
    merge_request_body = merge_request_response.json()
    if "merge_request_id" not in merge_request_body:
        fail(f"merge request response missing merge_request_id: {merge_request_body}")
    merge_request_id = merge_request_body["merge_request_id"]
    print(f"opened merge_request_id={merge_request_id}")

    step("Step 2e: assert the diff endpoint reports a conflict")
    diff_response = requests.get(f"{BASE_URL}/api/merge-requests/{merge_request_id}/diff")
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
    print("This script assumes the backend is already running (docker compose, or a local uvicorn).")

    create_user()

    markdown_artifact_id = ingest_markdown()
    chatgpt_artifact_id = ingest_chatgpt()

    create_conflicting_branch_and_merge(markdown_artifact_id)

    run_search([markdown_artifact_id, chatgpt_artifact_id])

    print("\nAll smoke test steps passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()

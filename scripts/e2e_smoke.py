#!/usr/bin/env python3
"""
End to end smoke test for Git for Research.

This script requires `docker compose up --build` to already be running
against the root docker-compose.yml before it is executed. It is meant
to be run manually as the final integration check against a live stack,
not as part of the pytest suite, since it makes real HTTP calls across
service boundaries and depends on container networking and timing.

As of this writing, the backend only exposes GET /health -- the
ingestion / branch / commit / merge-request / search HTTP routes this
script calls are the intended final shape of the API described in the
project plan, but the FastAPI route layer wiring them up to the
already-built ingestion, versioning, and retrieval modules has not been
built yet (see README.md, "What wasn't completed"). Running this script
today will fail at the first request with a 404. It is included so the
route layer's contract is pinned down precisely, and so that this
becomes a runnable, meaningful check as soon as those routes exist.

Usage:
    python scripts/e2e_smoke.py
    (or, using the backend's virtualenv which already has `requests`:
     backend/.venv/bin/python scripts/e2e_smoke.py)
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

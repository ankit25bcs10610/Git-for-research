#!/usr/bin/env python3
"""
End-to-end demo of the Git for Research versioning + retrieval engine,
run directly against the built Python modules (no HTTP involved -- for
the HTTP route layer, see scripts/e2e_smoke.py and README.md instead).
This is what actually gets exercised:

  1. Ingest two artifacts (a markdown doc, a ChatGPT export).
  2. Commit + branch the markdown doc, make CONFLICTING edits to the same
     paragraph on two branches.
  3. Show a live semantic diff between the two branches.
  4. Open a merge request, show the live merge conflict it detects.
  5. Resolve the conflict, merge, and prove the result is a real two-parent
     merge commit (not a linear history rewrite).
  6. Have an LLM "agent" (a fake, injected callable -- no external API
     dependency) open its own branch, propose an edit, and submit a merge
     request for human review.
  7. Chunk + embed everything with local sentence-transformers embeddings,
     and answer a natural-language question via pgvector similarity search,
     with every result tied back to its source artifact and commit.
  8. Record and walk a provenance edge from the answer back to its source.

Requires: the backend virtualenv (backend/.venv) with requirements.txt
installed, and a reachable Postgres+pgvector instance (default
DATABASE_URL: postgresql://research:research@localhost:5432/research).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import inspect as sa_inspect

from app.artifacts import create_artifact
from app.db.base import Base, engine, get_session
from app.ingestion.chatgpt_parser import parse_chatgpt_export
from app.ingestion.markdown_parser import parse_markdown
from app.versioning.dag_adapter import DagVersionedArtifact
from app.versioning.dag_store import get_commit, update_branch_head
from app.versioning.diff_engine import tokenize_paragraphs
from app.collab.merge_requests import create_merge_request, get_merge_request_diff, merge_merge_request
from app.collab.agent_editor import agent_edit
from app.retrieval.chunker import chunk_prose, chunk_messages
from app.retrieval.query import index_chunks, similarity_search
from app.retrieval.provenance import add_provenance_edge, trace_provenance
from app.users import create_user, get_user_by_username

import uuid


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


MARKDOWN_DOC = """# ATP Research Notes

## Introduction

Mitochondria are membrane bound organelles found in most eukaryotic cells.

## Findings

The paragraph under study describes ATP production in the citric acid cycle.
"""

CHATGPT_EXPORT = json.dumps([
    {
        "title": "Sample Research Chat",
        "mapping": {
            "root": {"id": "root", "message": None, "parent": None, "children": ["n1"]},
            "n1": {
                "id": "n1",
                "message": {
                    "author": {"role": "user"},
                    "content": {"parts": ["What is the boiling point of water at sea level?"]},
                    "create_time": 1000.0,
                },
                "parent": "root",
                "children": ["n2"],
            },
            "n2": {
                "id": "n2",
                "message": {
                    "author": {"role": "assistant"},
                    "content": {"parts": ["Water boils at 100 degrees Celsius at sea level."]},
                    "create_time": 1001.0,
                },
                "parent": "n1",
                "children": [],
            },
        },
    }
]).encode("utf-8")


def main() -> None:
    header("Setup: ensure schema exists (non-destructive, checkfirst)")
    Base.metadata.create_all(engine, checkfirst=True)
    print("Schema OK.")

    with get_session() as session:
        # This script calls the versioning/collab modules directly instead of
        # going through the HTTP route layer (see the module docstring), so
        # routes_versioning.py's require_user() check never runs -- without
        # this, every commit below would be attributed to "user-1" even
        # though no such row exists in `users`.
        try:
            get_user_by_username(session, "user-1")
        except ValueError:
            create_user(session, "user-1", "Demo User")

        # get_merge_request_diff/merge_merge_request look up the artifact's
        # real row (to pick a tokenizer by type -- see merge_requests.py), so
        # a bare uuid with no `artifacts` row behind it 404s once a merge
        # request is opened on it below.
        workspace_id = str(uuid.uuid4())
        artifact_id = create_artifact(session, workspace_id, "doc", "atp-notes.md")

        # --- 1. Ingestion -------------------------------------------------
        header("1. Ingestion")
        doc = parse_markdown(MARKDOWN_DOC.encode("utf-8"), "atp-notes.md")
        print(f"Parsed markdown artifact: type={doc.artifact_type!r} name={doc.name!r}")

        chat_artifacts = parse_chatgpt_export(CHATGPT_EXPORT)
        chat = chat_artifacts[0]
        print(f"Parsed ChatGPT export artifact: type={chat.artifact_type!r} name={chat.name!r}")
        chat_messages = json.loads(chat.content)
        print(f"  -> {len(chat_messages)} messages flattened from the export's tree structure")

        # --- 2. Commit + branch + CONFLICTING edits ------------------------
        header("2. Versioning: commit, branch, and two conflicting edits")
        artifact = DagVersionedArtifact(session, artifact_id, tokenize_paragraphs)

        root = artifact.commit(doc.content, "user-1", "initial import", None)
        artifact.branch("main", root)
        artifact.branch("edit-atp-location", root)
        print(f"Root commit: {root}")
        print("Branches created: main, edit-atp-location (both point at root)")

        main_edit_content = doc.content.replace(
            "The paragraph under study describes ATP production in the citric acid cycle.",
            "The paragraph under study describes ATP production during oxidative phosphorylation.",
        )
        main_commit = artifact.commit(main_edit_content, "user-1", "clarify ATP production mechanism", root)
        update_branch_head(session, artifact_id, "main", main_commit)
        print(f"Committed to main:               {main_commit}")

        branch_edit_content = doc.content.replace(
            "The paragraph under study describes ATP production in the citric acid cycle.",
            "The paragraph under study describes ATP synthesis inside the mitochondrial matrix.",
        )
        branch_commit = artifact.commit(branch_edit_content, "user-1", "clarify ATP synthesis location", root)
        update_branch_head(session, artifact_id, "edit-atp-location", branch_commit)
        print(f"Committed to edit-atp-location:  {branch_commit}")
        print("\nBoth branches edited the SAME paragraph differently since forking from root.")

        # --- 3. Live semantic diff -----------------------------------------
        header("3. Live semantic diff (main vs. edit-atp-location)")
        diff_entries = artifact.diff(main_commit, branch_commit)
        for entry in diff_entries:
            if entry["kind"] == "unchanged":
                print(f"  [unchanged] {entry['text'][:60]}")
            elif entry["kind"] == "changed":
                print(f"  [CHANGED]   old: {entry['old_text']}")
                print(f"              new: {entry['text']}")
                print(f"              word-level diff: {entry['word_diff']}")
            else:
                print(f"  [{entry['kind'].upper()}] {entry['text'][:60]}")

        # --- 4. Live merge conflict ------------------------------------------
        header("4. Live merge conflict")
        mr_id = create_merge_request(session, artifact_id, "edit-atp-location", "main", "user-1")
        print(f"Opened merge request {mr_id}: edit-atp-location -> main")

        diff_result = get_merge_request_diff(session, mr_id)
        assert len(diff_result["conflicts"]) == 1, "expected exactly one conflict"
        conflict = diff_result["conflicts"][0]
        print("Conflict detected:")
        print(f"  position: {conflict['position']}")
        print(f"  base:     {conflict['base']}")
        print(f"  ours:     {conflict['ours']}")
        print(f"  theirs:   {conflict['theirs']}")

        blocked = merge_merge_request(session, mr_id, resolutions=None, merged_by="user-1")
        assert blocked is False, "merge should be blocked until the conflict is resolved"
        print("\nmerge_merge_request(resolutions=None) correctly returned False -- blocked on the open conflict.")

        # --- 5. Resolve + merge, prove it's a real merge commit -------------
        header("5. Resolve the conflict and merge")
        resolved = merge_merge_request(
            session,
            mr_id,
            resolutions={conflict["position"]: "The paragraph under study describes ATP production during oxidative phosphorylation in the mitochondrial matrix."},
            merged_by="user-1",
        )
        assert resolved is True, "merge should succeed once the conflict is resolved"
        print("Merge succeeded.")

        new_main_head = artifact.branch_head("main")
        merge_commit = get_commit(session, new_main_head)
        print(f"New main head: {new_main_head}")
        print(f"Merge commit parent_ids: {merge_commit.parent_ids}")
        assert len(merge_commit.parent_ids) == 2, "resolved merge must be a real two-parent merge commit"
        assert main_commit in merge_commit.parent_ids and branch_commit in merge_commit.parent_ids
        print("Confirmed: BOTH branches are recorded as parents (a genuine merge, not a linear rewrite).")

        final_content = artifact.get_content(new_main_head)
        print("\nFinal merged content:\n" + "-" * 40)
        print(final_content)
        print("-" * 40)

        # --- 6. Multi-agent editing ------------------------------------------
        header("6. Multi-agent editing (LLM agent proposes an edit for human review)")

        def fake_llm_call(instruction: str, current_content: str) -> str:
            return current_content + "\n\n## Follow-up\n\nA deeper breakdown by contributor is available on request."

        agent_mr_id = agent_edit(
            session, artifact_id, "main", "Append a follow-up section.", fake_llm_call, "user-1"
        )
        agent_mr = get_merge_request_diff(session, agent_mr_id)
        print(f"Agent opened merge request {agent_mr_id} (status: open, awaiting human review)")
        print(f"Agent's proposed diff has {len(agent_mr['conflicts'])} conflicts (0 expected, since main hasn't moved since the agent forked)")
        agent_merged = merge_merge_request(session, agent_mr_id, resolutions=None, merged_by="user-1")
        print(f"Human reviewer approves -> merge_merge_request returned {agent_merged}")
        assert agent_merged is True

        # --- 7. Retrieval: chunk, embed, and answer a question ---------------
        header("7. Retrieval: chunk + embed + semantic search")
        final_head = artifact.branch_head("main")
        final_text = artifact.get_content(final_head)
        doc_chunks = chunk_prose(final_text)
        doc_chunk_ids = index_chunks(session, artifact_id, final_head, doc_chunks)
        print(f"Indexed {len(doc_chunk_ids)} paragraph chunks from the research doc")

        chat_artifact_id = str(uuid.uuid4())
        chat_chunks = chunk_messages(chat.content)
        chat_chunk_ids = index_chunks(session, chat_artifact_id, "n/a", chat_chunks)
        print(f"Indexed {len(chat_chunk_ids)} message chunks from the ChatGPT export")

        question = "How is ATP produced in the mitochondria?"
        print(f"\nQuery: {question!r}")
        results = similarity_search(session, question, top_k=3)
        for i, r in enumerate(results, 1):
            print(f"  #{i} (score={r['score']:.4f}) artifact={r['artifact_id'][:8]}... commit={str(r['commit_ref'])[:8]}...")
            print(f"      {r['text']}")

        assert results, "expected at least one search result"
        top_result = results[0]
        assert "ATP" in top_result["text"] or "mitochondria" in top_result["text"].lower() or "oxidative" in top_result["text"].lower(), (
            "expected the ATP-related paragraph to rank first for an ATP question"
        )
        print("\nConfirmed: the top hit is the ATP-related paragraph, not the unrelated chat message.")

        # --- 8. Provenance ----------------------------------------------------
        header("8. Provenance graph")
        answer_chunk_id = top_result["chunk_id"]
        source_chunk_id = doc_chunk_ids[0]
        add_provenance_edge(session, answer_chunk_id, source_chunk_id, "cites")
        chain = trace_provenance(session, answer_chunk_id)
        print(f"Recorded provenance edge: answer chunk {answer_chunk_id[:8]}... cites source chunk {source_chunk_id[:8]}...")
        print(f"trace_provenance walk: {chain}")
        assert chain and chain[0]["chunk_id"] == source_chunk_id

    header("All steps completed successfully.")
    print("Ingestion, versioning (commit/branch/diff/merge/conflict), multi-agent")
    print("editing, retrieval, and provenance all verified end-to-end against real")
    print("Postgres + pgvector + local sentence-transformers embeddings.")


if __name__ == "__main__":
    main()

import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchArtifacts, fetchDiff, fetchMergeRequest, submitResolution, searchQuery } from "./client";
import type { ConflictRecord } from "./client";

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

describe("searchQuery", () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  it("fetches GET /api/search with the q parameter url encoded and maps the response", async () => {
    const mockResponse = [
      {
        chunk_id: "chunk-1",
        text: "the mitochondria is the powerhouse of the cell",
        artifact_id: "artifact-1",
        commit_ref: "commit-abc",
        score: 0.87,
      },
    ];
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });

    const results = await searchQuery("mitochondria function");

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/search?q=mitochondria%20function")
    );
    expect(results).toEqual([
      {
        chunkId: "chunk-1",
        text: "the mitochondria is the powerhouse of the cell",
        artifactId: "artifact-1",
        commitRef: "commit-abc",
        score: 0.87,
      },
    ]);
  });
});

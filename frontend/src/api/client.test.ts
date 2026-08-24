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

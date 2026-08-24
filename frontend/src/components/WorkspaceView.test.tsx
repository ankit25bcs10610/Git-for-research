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

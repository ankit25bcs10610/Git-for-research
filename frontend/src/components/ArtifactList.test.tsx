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

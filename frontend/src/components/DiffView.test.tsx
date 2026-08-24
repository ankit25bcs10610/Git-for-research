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

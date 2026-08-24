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

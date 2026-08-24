import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PresenceIndicator } from "./PresenceIndicator";
import type { WebsocketProvider } from "y-websocket";

describe("PresenceIndicator", () => {
  it("renders a presence dot and label for each connected user", () => {
    const fakeStates = new Map([
      [1, { user: { name: "Alice", color: "#ff0000" } }],
      [2, { user: { name: "Bob", color: "#00ff00" } }],
    ]);
    const fakeAwareness = {
      getStates: () => fakeStates,
      on: () => {},
    };
    const fakeProvider = { awareness: fakeAwareness } as unknown as WebsocketProvider;

    render(<PresenceIndicator provider={fakeProvider} />);

    expect(screen.getByText("Alice")).toBeTruthy();
    expect(screen.getByText("Bob")).toBeTruthy();
    expect(screen.getByTestId("presence-dot-1")).toBeTruthy();
    expect(screen.getByTestId("presence-dot-2")).toBeTruthy();
  });
});

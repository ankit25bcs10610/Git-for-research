import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { LiveEditor } from "./LiveEditor";

vi.mock("y-websocket", () => {
  return {
    WebsocketProvider: vi.fn().mockImplementation(() => ({
      awareness: {
        getStates: () => new Map(),
        on: vi.fn(),
        off: vi.fn(),
      },
      destroy: vi.fn(),
    })),
  };
});

describe("LiveEditor", () => {
  it("renders a textarea and does not throw on mount or unmount", () => {
    expect(() => {
      const { unmount } = render(<LiveEditor roomId="room-1" wsUrl="ws://localhost:1234" />);
      expect(screen.getByRole("textbox")).toBeTruthy();
      unmount();
    }).not.toThrow();
  });
});

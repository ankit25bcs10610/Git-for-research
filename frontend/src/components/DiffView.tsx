import type { CSSProperties } from "react";
import type { DiffToken } from "../api/client";

const KIND_STYLES: Record<DiffToken["kind"], CSSProperties> = {
  unchanged: {},
  added: { backgroundColor: "#d4f8d4" },
  removed: { backgroundColor: "#f8d4d4", textDecoration: "line-through" },
  changed: { backgroundColor: "#fff3b0" },
};

export interface DiffViewProps {
  tokens: DiffToken[];
}

function WordDiff({ wordDiff }: { wordDiff: DiffToken[] }) {
  return (
    <span className="diff-word-diff">
      {wordDiff.map((word, index) => (
        <span
          key={index}
          data-testid={`diff-word-${word.kind}`}
          className={`diff-token diff-${word.kind}`}
          style={KIND_STYLES[word.kind]}
        >
          {word.text}
        </span>
      ))}
    </span>
  );
}

function DiffTokenItem({ token }: { token: DiffToken }) {
  if (token.kind === "changed" && token.wordDiff && token.wordDiff.length > 0) {
    return (
      <span
        data-testid="diff-changed"
        className="diff-token diff-changed"
        style={KIND_STYLES.changed}
      >
        <WordDiff wordDiff={token.wordDiff} />
      </span>
    );
  }

  return (
    <span
      data-testid={`diff-${token.kind}`}
      className={`diff-token diff-${token.kind}`}
      style={KIND_STYLES[token.kind]}
    >
      {token.text}
    </span>
  );
}

export function DiffView({ tokens }: DiffViewProps) {
  return (
    <div className="diff-view">
      {tokens.map((token, index) => (
        <DiffTokenItem key={index} token={token} />
      ))}
    </div>
  );
}

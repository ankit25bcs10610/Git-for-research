import { useState } from "react";
import type { ConflictRecord } from "../api/client";

export interface ConflictResolutionViewProps {
  conflicts: ConflictRecord[];
  onResolve: (resolutions: Record<number, string>) => void;
}

export function ConflictResolutionView({ conflicts, onResolve }: ConflictResolutionViewProps) {
  const [resolutions, setResolutions] = useState<Record<number, string>>({});
  const [draftText, setDraftText] = useState<Record<number, string>>({});

  const chooseOurs = (conflict: ConflictRecord) => {
    setResolutions((prev) => ({ ...prev, [conflict.position]: conflict.ours ?? "" }));
  };

  const chooseTheirs = (conflict: ConflictRecord) => {
    setResolutions((prev) => ({ ...prev, [conflict.position]: conflict.theirs ?? "" }));
  };

  const chooseCustom = (position: number) => {
    setResolutions((prev) => ({ ...prev, [position]: draftText[position] ?? "" }));
  };

  const updateDraft = (position: number, text: string) => {
    setDraftText((prev) => ({ ...prev, [position]: text }));
  };

  const allResolved = conflicts.every(
    (conflict) => resolutions[conflict.position] !== undefined
  );

  const handleSubmit = () => {
    onResolve(resolutions);
  };

  return (
    <div>
      {conflicts.map((conflict) => (
        <div key={conflict.position} data-testid={`conflict-${conflict.position}`}>
          <div>
            <div>
              <h4>Base</h4>
              <pre>{conflict.base}</pre>
            </div>
            <div>
              <h4>Ours</h4>
              <pre>{conflict.ours}</pre>
            </div>
            <div>
              <h4>Theirs</h4>
              <pre>{conflict.theirs}</pre>
            </div>
          </div>
          <button type="button" onClick={() => chooseOurs(conflict)}>
            Use Ours
          </button>
          <button type="button" onClick={() => chooseTheirs(conflict)}>
            Use Theirs
          </button>
          <textarea
            aria-label={`custom-resolution-${conflict.position}`}
            value={draftText[conflict.position] ?? ""}
            onChange={(event) => updateDraft(conflict.position, event.target.value)}
          />
          <button type="button" onClick={() => chooseCustom(conflict.position)}>
            Use Custom
          </button>
          {resolutions[conflict.position] !== undefined && (
            <p data-testid={`resolved-${conflict.position}`}>
              Resolved: {resolutions[conflict.position]}
            </p>
          )}
        </div>
      ))}
      <button type="button" onClick={handleSubmit} disabled={!allResolved}>
        Submit Merge
      </button>
    </div>
  );
}

import { useEffect, useState } from "react";
import { fetchArtifacts, type Artifact } from "../api/client";
import { ArtifactList } from "./ArtifactList";

export interface WorkspaceViewProps {
  workspaceId: string;
}

export function WorkspaceView({ workspaceId }: WorkspaceViewProps) {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;
    fetchArtifacts(workspaceId).then((result) => {
      if (isCurrent) {
        setArtifacts(result);
      }
    });
    return () => {
      isCurrent = false;
    };
  }, [workspaceId]);

  return (
    <div className="workspace-view">
      <ArtifactList artifacts={artifacts} onSelect={setSelectedId} />
      {selectedId !== null && (
        <p data-testid="selected-artifact-id">{selectedId}</p>
      )}
    </div>
  );
}

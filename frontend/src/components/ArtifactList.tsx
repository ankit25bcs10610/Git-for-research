import type { Artifact } from "../api/client";

export interface ArtifactListProps {
  artifacts: Artifact[];
  onSelect: (id: string) => void;
}

export function ArtifactList({ artifacts, onSelect }: ArtifactListProps) {
  return (
    <ul className="artifact-list">
      {artifacts.map((artifact) => (
        <li key={artifact.id}>
          <button type="button" onClick={() => onSelect(artifact.id)}>
            {artifact.name}
          </button>
        </li>
      ))}
    </ul>
  );
}

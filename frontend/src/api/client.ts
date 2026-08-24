export interface Artifact {
  id: string;
  workspaceId: string;
  type: string;
  name: string;
}

export interface DiffToken {
  kind: "unchanged" | "added" | "removed" | "changed";
  text: string;
  oldText?: string;
  wordDiff?: DiffToken[];
}

export async function fetchArtifacts(workspaceId: string): Promise<Artifact[]> {
  const response = await fetch(`/api/workspaces/${workspaceId}/artifacts`);
  return response.json();
}

export async function fetchDiff(
  artifactId: string,
  refA: string,
  refB: string
): Promise<DiffToken[]> {
  const params = new URLSearchParams({ ref_a: refA, ref_b: refB });
  const response = await fetch(`/api/artifacts/${artifactId}/diff?${params.toString()}`);
  return response.json();
}

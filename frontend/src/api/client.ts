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

export interface ConflictRecord {
  position: number;
  base?: string;
  ours?: string;
  theirs?: string;
}

export async function fetchMergeRequest(mrId: string): Promise<{ conflicts: ConflictRecord[] }> {
  const response = await fetch(`/api/merge-requests/${mrId}/diff`);
  if (!response.ok) {
    throw new Error(`fetchMergeRequest failed with status ${response.status}`);
  }
  return response.json();
}

export async function submitResolution(
  mrId: string,
  resolutions: Record<number, string>
): Promise<void> {
  const response = await fetch(`/api/merge-requests/${mrId}/merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resolutions }),
  });
  if (!response.ok) {
    throw new Error(`submitResolution failed with status ${response.status}`);
  }
}

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
export const CRDT_WS_URL = import.meta.env.VITE_CRDT_WS_URL ?? 'ws://localhost:1234'
const BASE_URL = `${API_BASE_URL}/api`

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, init)
  if (!response.ok) {
    const body = await response.text()
    throw new Error(`${init?.method ?? 'GET'} ${path} failed (${response.status}): ${body}`)
  }
  return response.json()
}

function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export interface Artifact {
  id: string
  workspaceId: string
  type: string
  name: string
}

export interface Branch {
  name: string
  head_commit_id: string
}

export interface DiffEntry {
  kind: 'unchanged' | 'removed' | 'added' | 'changed'
  text: string
  old_text: string | null
  word_diff?: DiffEntry[]
}

export interface MergeConflict {
  position: number
  base: string
  ours: string | null
  theirs: string | null
}

export interface MergeRequestSummary {
  id: string
  source_branch: string
  target_branch: string
  status: 'open' | 'merged' | 'rejected'
  opened_by: string
  merged_by: string | null
  rejected_by: string | null
}

export interface MergeRequestDiff {
  merged_tokens: string[]
  conflicts: MergeConflict[]
  has_conflict: boolean
}

export interface Commit {
  id: string
  message: string
  author: string
  created_at: string
}

export interface SearchResult {
  chunk_id: string
  text: string
  artifact_id: string
  commit_ref: string
  score: number
}

export interface GraphCommit {
  id: string
  parent_ids: string[]
  author: string
  message: string
  created_at: string
}

export interface ArtifactGraph {
  commits: GraphCommit[]
  branches: Branch[]
  merge_requests: MergeRequestSummary[]
}

export interface UserProfile {
  id: string
  username: string
  display_name: string
}

export function listUsers(): Promise<UserProfile[]> {
  return request('/users')
}

export function createUser(username: string, displayName?: string): Promise<UserProfile> {
  return postJson('/users', { username, display_name: displayName })
}

export type IngestKind = 'markdown' | 'chatgpt' | 'claude' | 'pdf'

export async function ingestArtifact(
  workspaceId: string,
  kind: IngestKind,
  file: File,
  author: string,
): Promise<string[]> {
  const form = new FormData()
  form.append('file', file)
  form.append('author', author)
  const body = await request<
    { artifact_id: string; commit_ref: string } | { artifacts: { artifact_id: string }[] }
  >(`/workspaces/${encodeURIComponent(workspaceId)}/artifacts/ingest/${kind}`, {
    method: 'POST',
    body: form,
  })
  if ('artifact_id' in body) return [body.artifact_id]
  return body.artifacts.map((a) => a.artifact_id)
}

export function listArtifacts(workspaceId: string): Promise<Artifact[]> {
  return request(`/workspaces/${encodeURIComponent(workspaceId)}/artifacts`)
}

export function listBranches(artifactId: string): Promise<Branch[]> {
  return request(`/artifacts/${artifactId}/branches`)
}

export function getArtifactGraph(artifactId: string): Promise<ArtifactGraph> {
  return request(`/artifacts/${artifactId}/graph`)
}

export function createBranch(artifactId: string, name: string, fromRef: string): Promise<Branch> {
  return postJson(`/artifacts/${artifactId}/branches`, { name, from_ref: fromRef })
}

export function createCommit(
  artifactId: string,
  branchName: string,
  content: string,
  message: string,
  author: string,
): Promise<{ commit_ref: string; branch_name: string }> {
  return postJson(`/artifacts/${artifactId}/commits`, { branch_name: branchName, content, message, author })
}

export function getContent(artifactId: string, ref: string): Promise<{ content: string }> {
  return request(`/artifacts/${artifactId}/content?ref=${encodeURIComponent(ref)}`)
}

export function getDiff(artifactId: string, refA: string, refB: string): Promise<{ entries: DiffEntry[] }> {
  return request(
    `/artifacts/${artifactId}/diff?ref_a=${encodeURIComponent(refA)}&ref_b=${encodeURIComponent(refB)}`,
  )
}

export function getChanges(artifactId: string, userId: string, branchName: string): Promise<Commit[]> {
  return request(
    `/artifacts/${artifactId}/changes?user_id=${encodeURIComponent(userId)}&branch_name=${encodeURIComponent(branchName)}`,
  )
}

export function markSeen(artifactId: string, userId: string, commitRef: string): Promise<{ status: string }> {
  return postJson(`/artifacts/${artifactId}/seen`, { user_id: userId, commit_ref: commitRef })
}

export function listMergeRequests(artifactId: string): Promise<MergeRequestSummary[]> {
  return request(`/artifacts/${artifactId}/merge-requests`)
}

export function createMergeRequest(
  artifactId: string,
  sourceBranch: string,
  targetBranch: string,
  author: string,
): Promise<{ merge_request_id: string }> {
  return postJson(`/artifacts/${artifactId}/merge-requests`, {
    source_branch: sourceBranch,
    target_branch: targetBranch,
    author,
  })
}

export function getMergeRequestDiff(mrId: string): Promise<MergeRequestDiff> {
  return request(`/merge-requests/${mrId}/diff`)
}

export async function mergeMergeRequest(
  mrId: string,
  resolutions: Record<number, string> | null,
  author: string,
): Promise<{ merged: boolean }> {
  const response = await fetch(`${BASE_URL}/merge-requests/${mrId}/merge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resolutions, author }),
  })
  const body = await response.json()
  if (!response.ok) {
    throw new Error(body.detail ?? `merge failed (${response.status})`)
  }
  return body
}

export function rejectMergeRequest(mrId: string, author: string): Promise<{ status: string }> {
  return postJson(`/merge-requests/${mrId}/reject`, { author })
}

export function agentEdit(
  artifactId: string,
  baseBranch: string,
  instruction: string,
  proposedContent: string,
  author: string,
): Promise<{ merge_request_id: string }> {
  return postJson(`/artifacts/${artifactId}/agent-edit`, {
    base_branch: baseBranch,
    instruction,
    proposed_content: proposedContent,
    author,
  })
}

export function search(query: string, topK = 5): Promise<SearchResult[]> {
  return request(`/search?q=${encodeURIComponent(query)}&top_k=${topK}`)
}

export interface AnswerResponse {
  answer: string
  sources: SearchResult[]
}

export function getAnswer(query: string, topK = 5): Promise<AnswerResponse> {
  return request(`/search/answer?q=${encodeURIComponent(query)}&top_k=${topK}`)
}

export function commitLiveSnapshot(
  artifactId: string,
  branchName: string,
  author: string,
): Promise<{ commit_ref: string }> {
  return postJson(`/artifacts/${artifactId}/live/commit-snapshot`, { branch_name: branchName, author })
}

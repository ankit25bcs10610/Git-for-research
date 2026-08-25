import { describe, expect, it } from 'vitest'
import { layoutMergeRequestEdges } from './CommitGraph3D'
import type { ArtifactGraph } from '../api'

function graph(overrides: Partial<ArtifactGraph> = {}): ArtifactGraph {
  return {
    commits: [
      { id: 'c1', parent_ids: [], author: 'user-1', message: 'root', created_at: '2026-01-01' },
      { id: 'c2', parent_ids: ['c1'], author: 'user-1', message: 'main edit', created_at: '2026-01-02' },
      { id: 'c3', parent_ids: ['c1'], author: 'user-1', message: 'feature edit', created_at: '2026-01-02' },
    ],
    branches: [
      { name: 'main', head_commit_id: 'c2' },
      { name: 'feature-a', head_commit_id: 'c3' },
    ],
    merge_requests: [],
    ...overrides,
  }
}

const positionById = new Map<string, [number, number, number]>([
  ['c1', [0, 0, 0]],
  ['c2', [0, 1.3, 0]],
  ['c3', [1.7, 1.3, 0]],
])

describe('layoutMergeRequestEdges', () => {
  it('produces an edge between the source and target branch heads for an open merge request', () => {
    const g = graph({
      merge_requests: [{ id: 'mr-1', source_branch: 'feature-a', target_branch: 'main', status: 'open' }],
    })

    const edges = layoutMergeRequestEdges(g, positionById)

    expect(edges).toEqual([
      {
        id: 'mr-1',
        sourceBranch: 'feature-a',
        targetBranch: 'main',
        status: 'open',
        sourcePosition: [1.7, 1.3, 0],
        targetPosition: [0, 1.3, 0],
      },
    ])
  })

  it('skips a merge request whose branch no longer exists in the graph', () => {
    const g = graph({
      merge_requests: [
        { id: 'mr-2', source_branch: 'deleted-branch', target_branch: 'main', status: 'open' },
      ],
    })

    expect(layoutMergeRequestEdges(g, positionById)).toEqual([])
  })

  it('returns one edge per merge request, including merged and rejected ones', () => {
    const g = graph({
      merge_requests: [
        { id: 'mr-1', source_branch: 'feature-a', target_branch: 'main', status: 'merged' },
        { id: 'mr-2', source_branch: 'feature-a', target_branch: 'main', status: 'rejected' },
      ],
    })

    const edges = layoutMergeRequestEdges(g, positionById)

    expect(edges.map((e) => e.id)).toEqual(['mr-1', 'mr-2'])
    expect(edges.map((e) => e.status)).toEqual(['merged', 'rejected'])
  })
})

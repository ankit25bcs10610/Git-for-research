import { useEffect, useMemo, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { Html, Line, OrbitControls } from '@react-three/drei'
import { motion } from 'framer-motion'
import {
  getArtifactGraph,
  type ArtifactGraph,
  type GraphCommit,
  type MergeRequestSummary,
} from '../api'

interface Props {
  artifactId: string
  refreshSignal: number
  onSelectCommit: (commitId: string) => void
}

const LANE_COLORS = ['#22d3ee', '#a78bfa', '#fb923c', '#f472b6', '#4ade80', '#facc15']
const LANE_SPACING = 1.7
const DEPTH_SPACING = 1.3

const MR_STATUS_COLORS: Record<MergeRequestSummary['status'], string> = {
  open: '#f59e0b',
  merged: '#34d399',
  rejected: '#64748b',
}

interface LaidOutCommit {
  commit: GraphCommit
  position: [number, number, number]
  lane: number
  isMerge: boolean
}

export interface MergeRequestEdge {
  id: string
  sourceBranch: string
  targetBranch: string
  status: MergeRequestSummary['status']
  sourcePosition: [number, number, number]
  targetPosition: [number, number, number]
}

export function layoutMergeRequestEdges(
  graph: ArtifactGraph,
  positionById: Map<string, [number, number, number]>,
): MergeRequestEdge[] {
  const headCommitIdByBranch = new Map(graph.branches.map((b) => [b.name, b.head_commit_id]))
  const edges: MergeRequestEdge[] = []
  for (const mr of graph.merge_requests) {
    const sourceHead = headCommitIdByBranch.get(mr.source_branch)
    const targetHead = headCommitIdByBranch.get(mr.target_branch)
    const sourcePosition = sourceHead ? positionById.get(sourceHead) : undefined
    const targetPosition = targetHead ? positionById.get(targetHead) : undefined
    if (!sourcePosition || !targetPosition) continue
    edges.push({
      id: mr.id,
      sourceBranch: mr.source_branch,
      targetBranch: mr.target_branch,
      status: mr.status,
      sourcePosition,
      targetPosition,
    })
  }
  return edges
}

function jitter(id: string): number {
  let hash = 0
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) >>> 0
  return ((hash % 100) / 100 - 0.5) * 0.5
}

function layoutGraph(graph: ArtifactGraph): { nodes: LaidOutCommit[]; edges: [string, string][] } {
  const commitById = new Map(graph.commits.map((c) => [c.id, c]))

  const depthById = new Map<string, number>()
  function depthOf(id: string): number {
    if (depthById.has(id)) return depthById.get(id)!
    const commit = commitById.get(id)
    if (!commit || commit.parent_ids.length === 0) {
      depthById.set(id, 0)
      return 0
    }
    const d = 1 + Math.max(...commit.parent_ids.map((p) => (commitById.has(p) ? depthOf(p) : -1)))
    depthById.set(id, d)
    return d
  }
  graph.commits.forEach((c) => depthOf(c.id))

  const laneById = new Map<string, number>()
  const sortedBranches = [...graph.branches].sort((a, b) =>
    a.name === 'main' ? -1 : b.name === 'main' ? 1 : a.name.localeCompare(b.name),
  )
  sortedBranches.forEach((branch, laneIndex) => {
    let cursor: string | undefined = branch.head_commit_id
    while (cursor && !laneById.has(cursor)) {
      laneById.set(cursor, laneIndex)
      cursor = commitById.get(cursor)?.parent_ids[0]
    }
  })
  graph.commits.forEach((c) => {
    if (!laneById.has(c.id)) laneById.set(c.id, 0)
  })

  const nodes: LaidOutCommit[] = graph.commits.map((commit) => {
    const lane = laneById.get(commit.id) ?? 0
    const depth = depthById.get(commit.id) ?? 0
    return {
      commit,
      lane,
      isMerge: commit.parent_ids.length > 1,
      position: [lane * LANE_SPACING, depth * DEPTH_SPACING, jitter(commit.id)],
    }
  })

  const edges: [string, string][] = []
  graph.commits.forEach((c) => c.parent_ids.forEach((p) => {
    if (commitById.has(p)) edges.push([p, c.id])
  }))

  return { nodes, edges }
}

function CommitNode({ node, onSelect }: { node: LaidOutCommit; onSelect: (id: string) => void }) {
  const [hovered, setHovered] = useState(false)
  const color = node.isMerge ? '#ffffff' : LANE_COLORS[node.lane % LANE_COLORS.length]

  return (
    <group position={node.position}>
      <mesh
        onClick={(e) => {
          e.stopPropagation()
          onSelect(node.commit.id)
        }}
        onPointerOver={(e) => {
          e.stopPropagation()
          setHovered(true)
        }}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[node.isMerge ? 0.16 : 0.12, 24, 24]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={hovered ? 1.4 : 0.6}
          roughness={0.3}
        />
      </mesh>
      {hovered && (
        <Html distanceFactor={8} style={{ pointerEvents: 'none' }}>
          <div className="whitespace-nowrap rounded-md border border-slate-700 bg-slate-950/95 px-2 py-1 text-xs text-slate-100 shadow-lg">
            <div className="font-mono text-cyan-300">{node.commit.id.slice(0, 8)}</div>
            <div>{node.commit.message}</div>
            <div className="text-slate-400">{node.commit.author}</div>
          </div>
        </Html>
      )}
    </group>
  )
}

export default function CommitGraph3D({ artifactId, refreshSignal, onSelectCommit }: Props) {
  const [graph, setGraph] = useState<ArtifactGraph | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getArtifactGraph(artifactId)
      .then(setGraph)
      .catch((err) => setError((err as Error).message))
  }, [artifactId, refreshSignal])

  const layout = useMemo(() => (graph ? layoutGraph(graph) : null), [graph])

  if (error) return <p className="text-sm text-rose-400">{error}</p>
  if (!layout) return <p className="text-sm text-stone-500 dark:text-slate-400">Loading commit graph…</p>
  if (layout.nodes.length === 0) {
    return <p className="text-sm italic text-stone-500 dark:text-slate-400">No commits yet — this artifact's history will render here.</p>
  }

  const positionById = new Map(layout.nodes.map((n) => [n.commit.id, n.position]))
  const mergeRequestEdges = layoutMergeRequestEdges(graph!, positionById)

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="h-80 w-full overflow-hidden rounded-lg border border-stone-200 bg-stone-50 dark:border-slate-800 dark:bg-black"
    >
      <Canvas camera={{ position: [3, 3, 5], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[5, 5, 5]} intensity={60} />
        {layout.edges.map(([fromId, toId]) => {
          const a = positionById.get(fromId)
          const b = positionById.get(toId)
          if (!a || !b) return null
          return <Line key={`${fromId}-${toId}`} points={[a, b]} color="#475569" lineWidth={1.5} />
        })}
        {layout.nodes.map((node) => (
          <CommitNode key={node.commit.id} node={node} onSelect={onSelectCommit} />
        ))}
        {mergeRequestEdges.map((edge) => {
          const color = MR_STATUS_COLORS[edge.status]
          const midpoint: [number, number, number] = [
            (edge.sourcePosition[0] + edge.targetPosition[0]) / 2,
            (edge.sourcePosition[1] + edge.targetPosition[1]) / 2,
            (edge.sourcePosition[2] + edge.targetPosition[2]) / 2,
          ]
          return (
            <group key={edge.id}>
              <Line
                points={[edge.sourcePosition, edge.targetPosition]}
                color={color}
                lineWidth={2}
                dashed
                dashSize={0.15}
                gapSize={0.1}
              />
              <Html position={midpoint} distanceFactor={8} style={{ pointerEvents: 'none' }}>
                <div
                  className="whitespace-nowrap rounded-md border bg-slate-950/95 px-2 py-0.5 text-[10px] font-medium shadow-lg"
                  style={{ borderColor: color, color }}
                >
                  MR: {edge.sourceBranch} → {edge.targetBranch} ({edge.status})
                </div>
              </Html>
            </group>
          )
        })}
        <OrbitControls enablePan enableZoom enableRotate makeDefault />
      </Canvas>
    </motion.div>
  )
}

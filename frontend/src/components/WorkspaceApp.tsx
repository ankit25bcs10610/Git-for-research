import { useEffect, useState } from 'react'
import IngestPanel from './IngestPanel'
import ArtifactList from './ArtifactList'
import BranchesPanel from './BranchesPanel'
import DiffPanel from './DiffPanel'
import MergeRequestsPanel from './MergeRequestsPanel'
import ChangesPanel from './ChangesPanel'
import AgentEditPanel from './AgentEditPanel'
import SearchPanel from './SearchPanel'
import CommitGraph3D from './CommitGraph3D'
import LiveEditor from './LiveEditor'
import CodebaseBranchesPanel from './CodebaseBranchesPanel'
import CodebaseDiffPanel from './CodebaseDiffPanel'
import CodebaseMergeRequestsPanel from './CodebaseMergeRequestsPanel'
import Card from './ui/Card'
import { API_BASE_URL, getArtifact, type Artifact } from '../api'

interface Props {
  onBack: () => void
}

export default function WorkspaceApp({ onBack }: Props) {
  const [workspaceId, setWorkspaceId] = useState('demo-workspace')
  const [activeArtifactId, setActiveArtifactId] = useState<string | null>(null)
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null)
  const [refreshSignal, setRefreshSignal] = useState(0)
  const [focusedRef, setFocusedRef] = useState<string | null>(null)

  useEffect(() => {
    if (!activeArtifactId) {
      setActiveArtifact(null)
      return
    }
    getArtifact(activeArtifactId)
      .then(setActiveArtifact)
      .catch(() => setActiveArtifact(null))
  }, [activeArtifactId, refreshSignal])

  function bump() {
    setRefreshSignal((n) => n + 1)
  }

  return (
    <div>
      <header className="mx-auto mb-6 max-w-4xl rounded-xl border border-stone-200/70 bg-white/70 p-5 shadow-sm backdrop-blur-md dark:border-slate-800/70 dark:bg-slate-900/50">
        <button
          onClick={onBack}
          className="mb-3 text-sm text-stone-600 transition-colors hover:text-stone-900 dark:text-slate-400 dark:hover:text-slate-100"
        >
          ← Back to overview
        </button>
        <h1 className="bg-gradient-to-r from-stone-900 to-stone-600 bg-clip-text text-2xl font-bold tracking-tight text-transparent dark:from-cyan-300 dark:to-violet-400">
          Git for Research
        </h1>
        <p className="mt-1 max-w-xl text-sm text-stone-600 dark:text-slate-400">
          Wired to the live backend at{' '}
          <code className="rounded bg-stone-200/80 px-1 py-0.5 dark:bg-slate-800/80">{API_BASE_URL}</code>.
        </p>
        <div className="mt-4 flex items-center gap-2">
          <span className="text-sm font-semibold text-stone-700 dark:text-slate-300">Workspace:</span>
          <input
            value={workspaceId}
            onChange={(e) => setWorkspaceId(e.target.value)}
            className="w-56 rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
          />
        </div>
      </header>

      <div className="mx-auto max-w-4xl space-y-4">
        <IngestPanel
          workspaceId={workspaceId}
          onIngested={(ids) => {
            bump()
            if (ids[0]) setActiveArtifactId(ids[0])
          }}
        />

        <ArtifactList
          workspaceId={workspaceId}
          activeArtifactId={activeArtifactId}
          onSelect={setActiveArtifactId}
          refreshSignal={refreshSignal}
        />

        {activeArtifactId && activeArtifact?.type === 'codebase' ? (
          <>
            <p className="text-xs italic text-stone-500 dark:text-slate-500">
              Codebase artifact — real git history on disk (branches/commits/merges via pygit2), not the
              Postgres-backed commit graph above. Semantic search, live co-editing, and agent-edit apply to
              doc/chat/pdf artifacts only.
            </p>
            <CodebaseBranchesPanel artifactId={activeArtifactId} refreshSignal={refreshSignal} onChanged={bump} />
            <CodebaseDiffPanel artifactId={activeArtifactId} />
            <CodebaseMergeRequestsPanel artifactId={activeArtifactId} refreshSignal={refreshSignal} onChanged={bump} />
          </>
        ) : activeArtifactId ? (
          <>
            <Card title="Commit graph">
              <CommitGraph3D
                artifactId={activeArtifactId}
                refreshSignal={refreshSignal}
                onSelectCommit={setFocusedRef}
              />
              <p className="mt-2 text-xs text-stone-500 dark:text-slate-500">
                Drag to orbit, scroll to zoom, click a commit to view its content below.
              </p>
            </Card>
            <BranchesPanel
              artifactId={activeArtifactId}
              refreshSignal={refreshSignal}
              onChanged={bump}
              focusRef={focusedRef}
            />
            <LiveEditor artifactId={activeArtifactId} onCommitted={bump} />
            <DiffPanel artifactId={activeArtifactId} />
            <MergeRequestsPanel artifactId={activeArtifactId} refreshSignal={refreshSignal} onChanged={bump} />
            <ChangesPanel artifactId={activeArtifactId} refreshSignal={refreshSignal} />
            <AgentEditPanel artifactId={activeArtifactId} onChanged={bump} />
          </>
        ) : (
          <p className="text-sm italic text-stone-500 dark:text-slate-500">
            Ingest or select an artifact above to see its commit graph, branches, diffs, and merge requests.
          </p>
        )}

        <SearchPanel />
      </div>
    </div>
  )
}

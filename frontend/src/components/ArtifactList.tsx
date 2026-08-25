import { useEffect, useState } from 'react'
import { listArtifacts, type Artifact } from '../api'
import Card from './ui/Card'

interface Props {
  workspaceId: string
  activeArtifactId: string | null
  onSelect: (artifactId: string) => void
  refreshSignal: number
}

export default function ArtifactList({ workspaceId, activeArtifactId, onSelect, refreshSignal }: Props) {
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    listArtifacts(workspaceId)
      .then(setArtifacts)
      .catch((err) => setError((err as Error).message))
  }, [workspaceId, refreshSignal])

  return (
    <Card title={`2. Artifacts in workspace "${workspaceId}"`}>
      {error && <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>}
      {artifacts.length === 0 && !error && (
        <p className="text-sm text-stone-500 dark:text-slate-400">None yet — ingest one above.</p>
      )}
      <ul className="space-y-1">
        {artifacts.map((a) => (
          <li key={a.id}>
            <button
              onClick={() => onSelect(a.id)}
              className={`w-full rounded-md border px-2 py-1 text-left transition ${
                a.id === activeArtifactId
                  ? 'border-cyan-500 bg-stone-900 text-white dark:border-cyan-400 dark:bg-cyan-500/20 dark:text-cyan-100'
                  : 'border-stone-200 hover:bg-stone-100 dark:border-slate-800 dark:hover:bg-slate-800/60'
              }`}
            >
              <span className="mr-2 font-mono text-xs opacity-70">{a.type}</span>
              {a.name}
              <span className="block font-mono text-xs opacity-60">{a.id}</span>
            </button>
          </li>
        ))}
      </ul>
    </Card>
  )
}

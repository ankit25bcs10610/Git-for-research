import { useState } from 'react'
import { ingestArtifact, type IngestKind } from '../api'
import { useProfile } from '../profile/ProfileContext'
import Card from './ui/Card'

interface Props {
  workspaceId: string
  onIngested: (artifactIds: string[]) => void
}

const KINDS: { value: IngestKind; label: string }[] = [
  { value: 'markdown', label: 'Markdown / plaintext' },
  { value: 'chatgpt', label: 'ChatGPT export' },
  { value: 'claude', label: 'Claude export' },
  { value: 'pdf', label: 'PDF' },
]

const INPUT =
  'rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'

export default function IngestPanel({ workspaceId, onIngested }: Props) {
  const { profile } = useProfile()
  const [kind, setKind] = useState<IngestKind>('markdown')
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<string>('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setStatus('')
    try {
      const artifactIds = await ingestArtifact(workspaceId, kind, file, profile?.username ?? '')
      setStatus(`Ingested: ${artifactIds.join(', ')}`)
      onIngested(artifactIds)
      setFile(null)
    } catch (err) {
      setStatus(`Error: ${(err as Error).message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card title="1. Ingest an artifact">
      <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-2">
        <select className={INPUT} value={kind} onChange={(e) => setKind(e.target.value as IngestKind)}>
          {KINDS.map((k) => (
            <option key={k.value} value={k.value}>
              {k.label}
            </option>
          ))}
        </select>
        <input
          type="file"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm text-stone-700 dark:text-slate-300"
        />
        <button
          type="submit"
          disabled={!file || busy}
          className="rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-stone-700 disabled:opacity-50 dark:bg-cyan-500 dark:text-slate-950 dark:hover:bg-cyan-400"
        >
          {busy ? 'Ingesting…' : 'Ingest'}
        </button>
      </form>
      {status && <p className="mt-2 text-sm text-stone-600 dark:text-slate-400">{status}</p>}
    </Card>
  )
}

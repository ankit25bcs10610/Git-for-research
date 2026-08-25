import { useState } from 'react'
import { getCodebaseDiff, type CodebaseFileChange } from '../api'
import Card from './ui/Card'

interface Props {
  artifactId: string
}

const STATUS_STYLES: Record<CodebaseFileChange['status'], string> = {
  added: 'bg-green-100 text-green-900 dark:bg-emerald-500/10 dark:text-emerald-300',
  removed: 'bg-red-100 text-red-900 line-through dark:bg-rose-500/10 dark:text-rose-300',
  modified: 'bg-yellow-100 text-yellow-900 dark:bg-amber-500/10 dark:text-amber-300',
}

const INPUT =
  'rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'

export default function CodebaseDiffPanel({ artifactId }: Props) {
  const [refA, setRefA] = useState('master')
  const [refB, setRefB] = useState('')
  const [changes, setChanges] = useState<CodebaseFileChange[] | null>(null)
  const [status, setStatus] = useState('')

  async function handleDiff(e: React.FormEvent) {
    e.preventDefault()
    try {
      const { changes } = await getCodebaseDiff(artifactId, refA, refB)
      setChanges(changes)
      setStatus('')
    } catch (err) {
      setStatus((err as Error).message)
      setChanges(null)
    }
  }

  return (
    <Card title="Codebase: file-level diff between two refs">
      <form onSubmit={handleDiff} className="mb-3 flex items-center gap-2">
        <input
          value={refA}
          onChange={(e) => setRefA(e.target.value)}
          placeholder="ref A (e.g. master)"
          className={`${INPUT} w-40`}
        />
        <span className="text-sm text-stone-600 dark:text-slate-400">vs</span>
        <input
          value={refB}
          onChange={(e) => setRefB(e.target.value)}
          placeholder="ref B (e.g. a branch name)"
          required
          className={`${INPUT} w-40`}
        />
        <button
          type="submit"
          className="rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-stone-700 dark:bg-cyan-500 dark:text-slate-950 dark:hover:bg-cyan-400"
        >
          Diff
        </button>
      </form>
      {status && <p className="text-sm text-rose-600 dark:text-rose-400">{status}</p>}
      {changes && (
        <div className="space-y-1">
          {changes.map((c) => (
            <div key={c.path} className={`rounded-md px-2 py-1 font-mono text-sm ${STATUS_STYLES[c.status]}`}>
              <span className="mr-2 text-xs opacity-60">[{c.status}]</span>
              {c.path}
            </div>
          ))}
          {changes.length === 0 && <p className="text-sm text-stone-500 dark:text-slate-400">No file changes.</p>}
        </div>
      )}
    </Card>
  )
}

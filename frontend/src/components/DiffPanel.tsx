import { useState } from 'react'
import { getDiff, type DiffEntry } from '../api'
import Card from './ui/Card'

interface Props {
  artifactId: string
}

const KIND_STYLES: Record<DiffEntry['kind'], string> = {
  unchanged: 'bg-white text-stone-700 dark:bg-slate-900/40 dark:text-slate-300',
  added: 'bg-green-100 text-green-900 dark:bg-emerald-500/10 dark:text-emerald-300',
  removed: 'bg-red-100 text-red-900 line-through dark:bg-rose-500/10 dark:text-rose-300',
  changed: 'bg-yellow-100 text-yellow-900 dark:bg-amber-500/10 dark:text-amber-300',
}

const INPUT =
  'rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'

function WordDiff({ words }: { words: DiffEntry[] }) {
  return (
    <span>
      {words.map((w, i) => (
        <span
          key={i}
          className={
            w.kind === 'added'
              ? 'bg-green-200 dark:bg-emerald-500/30'
              : w.kind === 'removed'
                ? 'bg-red-200 line-through dark:bg-rose-500/30'
                : undefined
          }
        >
          {w.text}{' '}
        </span>
      ))}
    </span>
  )
}

export default function DiffPanel({ artifactId }: Props) {
  const [refA, setRefA] = useState('main')
  const [refB, setRefB] = useState('')
  const [entries, setEntries] = useState<DiffEntry[] | null>(null)
  const [status, setStatus] = useState('')

  async function handleDiff(e: React.FormEvent) {
    e.preventDefault()
    try {
      const { entries } = await getDiff(artifactId, refA, refB)
      setEntries(entries)
      setStatus('')
    } catch (err) {
      setStatus((err as Error).message)
      setEntries(null)
    }
  }

  return (
    <Card title="4. Semantic diff between two refs">
      <form onSubmit={handleDiff} className="mb-3 flex items-center gap-2">
        <input
          value={refA}
          onChange={(e) => setRefA(e.target.value)}
          placeholder="ref A (e.g. main)"
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
      {entries && (
        <div className="space-y-1">
          {entries.map((e, i) => (
            <div key={i} className={`rounded-md px-2 py-1 text-sm ${KIND_STYLES[e.kind]}`}>
              <span className="mr-2 font-mono text-xs opacity-60">[{e.kind}]</span>
              {e.kind === 'changed' && e.word_diff ? <WordDiff words={e.word_diff} /> : e.text}
            </div>
          ))}
          {entries.length === 0 && <p className="text-sm text-stone-500 dark:text-slate-400">No paragraphs to diff.</p>}
        </div>
      )}
    </Card>
  )
}

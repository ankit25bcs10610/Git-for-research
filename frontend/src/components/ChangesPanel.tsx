import { useEffect, useState } from 'react'
import { getChanges, markSeen, type Commit } from '../api'
import { useProfile } from '../profile/ProfileContext'
import Card from './ui/Card'

interface Props {
  artifactId: string
  refreshSignal: number
}

const INPUT =
  'rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'

export default function ChangesPanel({ artifactId, refreshSignal }: Props) {
  const { profile } = useProfile()
  const userId = profile?.username ?? ''
  const [branchName, setBranchName] = useState('main')
  const [commits, setCommits] = useState<Commit[]>([])
  const [status, setStatus] = useState('')

  function refresh() {
    getChanges(artifactId, userId, branchName)
      .then(setCommits)
      .catch((err) => setStatus((err as Error).message))
  }

  useEffect(() => {
    refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifactId, branchName, refreshSignal])

  async function handleMarkSeen() {
    if (commits.length === 0) return
    try {
      await markSeen(artifactId, userId, commits[commits.length - 1].id)
      setStatus(`Marked seen up to ${commits[commits.length - 1].id.slice(0, 8)}`)
      refresh()
    } catch (err) {
      setStatus((err as Error).message)
    }
  }

  return (
    <Card title={`6. What changed since I last looked (${userId})`}>
      <div className="mb-3 flex items-center gap-2">
        <span className="text-sm font-semibold text-stone-700 dark:text-slate-300">Branch:</span>
        <input value={branchName} onChange={(e) => setBranchName(e.target.value)} className={`${INPUT} w-32`} />
        <button
          onClick={handleMarkSeen}
          disabled={commits.length === 0}
          className="rounded-md bg-stone-200 px-3 py-1.5 text-sm font-medium text-stone-800 transition hover:bg-stone-300 disabled:opacity-50 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          Mark as seen
        </button>
      </div>
      {commits.length === 0 ? (
        <p className="text-sm text-stone-500 dark:text-slate-400">Nothing new since last seen.</p>
      ) : (
        <ul className="space-y-1 text-sm">
          {commits.map((c) => (
            <li
              key={c.id}
              className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 dark:border-amber-500/30 dark:bg-amber-500/10"
            >
              <span className="mr-2 font-mono text-xs opacity-70">{c.id.slice(0, 8)}</span>
              {c.message}{' '}
              <span className="opacity-60">
                — {c.author}, {new Date(c.created_at).toLocaleString()}
              </span>
            </li>
          ))}
        </ul>
      )}
      {status && <p className="mt-2 text-sm text-stone-600 dark:text-slate-400">{status}</p>}
    </Card>
  )
}

import { useEffect, useState } from 'react'
import {
  createCodebaseMergeRequest,
  getCodebaseMergeRequestDiff,
  listCodebaseMergeRequests,
  mergeCodebaseMergeRequest,
  rejectCodebaseMergeRequest,
  type CodebaseMergeRequestDiff,
  type MergeRequestSummary,
} from '../api'
import { useProfile } from '../profile/ProfileContext'
import Card from './ui/Card'

interface Props {
  artifactId: string
  refreshSignal: number
  onChanged: () => void
}

const INPUT =
  'rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'

export default function CodebaseMergeRequestsPanel({ artifactId, refreshSignal, onChanged }: Props) {
  const { profile } = useProfile()
  const [mergeRequests, setMergeRequests] = useState<MergeRequestSummary[]>([])
  const [sourceBranch, setSourceBranch] = useState('')
  const [targetBranch, setTargetBranch] = useState('master')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [diff, setDiff] = useState<CodebaseMergeRequestDiff | null>(null)
  const [resolutions, setResolutions] = useState<Record<string, string>>({})
  const [status, setStatus] = useState('')

  function refresh() {
    listCodebaseMergeRequests(artifactId)
      .then(setMergeRequests)
      .catch((err) => setStatus((err as Error).message))
  }

  useEffect(() => {
    refresh()
    setSelectedId(null)
    setDiff(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifactId, refreshSignal])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      const { merge_request_id } = await createCodebaseMergeRequest(
        artifactId,
        sourceBranch,
        targetBranch,
        profile?.username ?? '',
      )
      setStatus(`Opened merge request ${merge_request_id}`)
      refresh()
      onChanged()
    } catch (err) {
      setStatus((err as Error).message)
    }
  }

  async function handleSelect(mrId: string) {
    setSelectedId(mrId)
    try {
      const d = await getCodebaseMergeRequestDiff(mrId)
      setDiff(d)
      const initial: Record<string, string> = {}
      for (const c of d.conflicts) initial[c.path] = c.ours ?? c.theirs ?? c.base ?? ''
      setResolutions(initial)
    } catch (err) {
      setStatus((err as Error).message)
    }
  }

  async function handleMerge() {
    if (!selectedId || !diff) return
    try {
      await mergeCodebaseMergeRequest(selectedId, diff.has_conflict ? resolutions : null, profile?.username ?? '')
      setStatus('Merged.')
      setSelectedId(null)
      setDiff(null)
      refresh()
      onChanged()
    } catch (err) {
      setStatus((err as Error).message)
    }
  }

  async function handleReject() {
    if (!selectedId) return
    await rejectCodebaseMergeRequest(selectedId, profile?.username ?? '')
    setStatus('Rejected.')
    setSelectedId(null)
    setDiff(null)
    refresh()
  }

  return (
    <Card title="Codebase: merge requests (real git merges, path-level conflicts)">
      <form onSubmit={handleCreate} className="mb-3 flex items-center gap-2">
        <input
          placeholder="source branch"
          value={sourceBranch}
          onChange={(e) => setSourceBranch(e.target.value)}
          required
          className={`${INPUT} w-32`}
        />
        <span className="text-sm text-stone-600 dark:text-slate-400">into</span>
        <input
          placeholder="target branch"
          value={targetBranch}
          onChange={(e) => setTargetBranch(e.target.value)}
          required
          className={`${INPUT} w-32`}
        />
        <button
          type="submit"
          className="rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-stone-700 dark:bg-cyan-500 dark:text-slate-950 dark:hover:bg-cyan-400"
        >
          Open merge request
        </button>
      </form>

      <ul className="mb-3 space-y-1">
        {mergeRequests.map((mr) => (
          <li key={mr.id}>
            <button
              onClick={() => handleSelect(mr.id)}
              className={`w-full rounded-md border px-2 py-1 text-left text-sm transition ${
                mr.id === selectedId
                  ? 'border-cyan-500 bg-stone-900 text-white dark:border-cyan-400 dark:bg-cyan-500/20 dark:text-cyan-100'
                  : 'border-stone-200 hover:bg-stone-100 dark:border-slate-800 dark:hover:bg-slate-800/60'
              }`}
            >
              {mr.source_branch} → {mr.target_branch}{' '}
              <span className="font-mono text-xs opacity-70">[{mr.status}]</span>{' '}
              <span className="text-xs opacity-70">opened by {mr.opened_by}</span>
            </button>
          </li>
        ))}
        {mergeRequests.length === 0 && <p className="text-sm text-stone-500 dark:text-slate-400">None yet.</p>}
      </ul>

      {diff && (
        <div className="border-t border-stone-200 pt-3 dark:border-slate-800">
          <p className="mb-2 text-sm">
            {diff.has_conflict ? (
              <span className="font-semibold text-rose-700 dark:text-rose-400">
                Conflict detected — resolve below before merging.
              </span>
            ) : (
              <span className="font-semibold text-emerald-700 dark:text-emerald-400">No conflicts — ready to merge.</span>
            )}
          </p>

          {diff.conflicts.map((c) => (
            <div key={c.path} className="mb-3 rounded-md border border-rose-300 bg-rose-50 p-2 dark:border-rose-900/60 dark:bg-rose-500/10">
              <p className="mb-1 font-mono text-xs opacity-70">{c.path}</p>
              <p className="text-xs">
                <span className="font-semibold">base:</span> {c.base ?? '(none)'}
              </p>
              <p className="text-xs">
                <span className="font-semibold">ours:</span> {c.ours ?? '(deleted)'}
              </p>
              <p className="text-xs">
                <span className="font-semibold">theirs:</span> {c.theirs ?? '(deleted)'}
              </p>
              <textarea
                value={resolutions[c.path] ?? ''}
                onChange={(e) => setResolutions({ ...resolutions, [c.path]: e.target.value })}
                rows={3}
                className={`${INPUT} mt-1 w-full font-mono`}
              />
            </div>
          ))}

          <div className="flex gap-2">
            <button onClick={handleMerge} className="rounded-md bg-emerald-700 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-emerald-600">
              Merge
            </button>
            <button
              onClick={handleReject}
              className="rounded-md bg-stone-200 px-3 py-1.5 text-sm font-medium text-stone-800 transition hover:bg-stone-300 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {status && <p className="mt-2 text-sm text-stone-600 dark:text-slate-400">{status}</p>}
    </Card>
  )
}

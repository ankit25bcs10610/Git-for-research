import { useEffect, useState } from 'react'
import { createBranch, createCommit, getContent, listBranches, type Branch } from '../api'
import Card from './ui/Card'

interface Props {
  artifactId: string
  refreshSignal: number
  onChanged: () => void
  focusRef?: string | null
}

const INPUT =
  'rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'
const BUTTON =
  'rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-stone-700 dark:bg-cyan-500 dark:text-slate-950 dark:hover:bg-cyan-400'

export default function BranchesPanel({ artifactId, refreshSignal, onChanged, focusRef }: Props) {
  const [branches, setBranches] = useState<Branch[]>([])
  const [newBranchName, setNewBranchName] = useState('')
  const [newBranchFrom, setNewBranchFrom] = useState('main')
  const [commitBranch, setCommitBranch] = useState('main')
  const [commitContent, setCommitContent] = useState('')
  const [commitMessage, setCommitMessage] = useState('')
  const [viewRef, setViewRef] = useState('main')
  const [viewedContent, setViewedContent] = useState<string | null>(null)
  const [status, setStatus] = useState('')

  function refresh() {
    listBranches(artifactId)
      .then(setBranches)
      .catch((err) => setStatus((err as Error).message))
  }

  useEffect(() => {
    refresh()
    setViewedContent(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifactId, refreshSignal])

  useEffect(() => {
    if (!focusRef) return
    setViewRef(focusRef)
    getContent(artifactId, focusRef)
      .then(({ content }) => setViewedContent(content))
      .catch((err) => setStatus((err as Error).message))
  }, [focusRef, artifactId])

  async function handleCreateBranch(e: React.FormEvent) {
    e.preventDefault()
    try {
      await createBranch(artifactId, newBranchName, newBranchFrom)
      setStatus(`Created branch "${newBranchName}" from ${newBranchFrom}`)
      setNewBranchName('')
      refresh()
      onChanged()
    } catch (err) {
      setStatus((err as Error).message)
    }
  }

  async function handleCommit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const result = await createCommit(artifactId, commitBranch, commitContent, commitMessage)
      setStatus(`Committed ${result.commit_ref} on ${result.branch_name}`)
      setCommitMessage('')
      refresh()
      onChanged()
    } catch (err) {
      setStatus((err as Error).message)
    }
  }

  async function handleView() {
    try {
      const { content } = await getContent(artifactId, viewRef)
      setViewedContent(content)
    } catch (err) {
      setStatus((err as Error).message)
    }
  }

  return (
    <Card title="3. Branches & commits">
      <div className="mb-3">
        <h3 className="mb-1 text-sm font-semibold text-stone-700 dark:text-slate-300">Branches</h3>
        <ul className="font-mono text-sm text-stone-800 dark:text-slate-200">
          {branches.map((b) => (
            <li key={b.name}>
              {b.name} → <span className="text-cyan-700 dark:text-cyan-400">{b.head_commit_id.slice(0, 8)}</span>
            </li>
          ))}
        </ul>
      </div>

      <form onSubmit={handleCreateBranch} className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-stone-700 dark:text-slate-300">New branch:</span>
        <input
          placeholder="branch name"
          value={newBranchName}
          onChange={(e) => setNewBranchName(e.target.value)}
          required
          className={INPUT}
        />
        <span className="text-sm text-stone-600 dark:text-slate-400">from</span>
        <input
          placeholder="main"
          value={newBranchFrom}
          onChange={(e) => setNewBranchFrom(e.target.value)}
          className={`${INPUT} w-24`}
        />
        <button type="submit" className={BUTTON}>
          Create
        </button>
      </form>

      <form onSubmit={handleCommit} className="mb-3 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-stone-700 dark:text-slate-300">Commit onto branch:</span>
          <input value={commitBranch} onChange={(e) => setCommitBranch(e.target.value)} className={`${INPUT} w-32`} />
          <input
            placeholder="commit message"
            value={commitMessage}
            onChange={(e) => setCommitMessage(e.target.value)}
            required
            className={`${INPUT} flex-1`}
          />
        </div>
        <textarea
          placeholder="new full content for this artifact"
          value={commitContent}
          onChange={(e) => setCommitContent(e.target.value)}
          required
          rows={4}
          className={`${INPUT} w-full font-mono`}
        />
        <button type="submit" className={BUTTON}>
          Commit
        </button>
      </form>

      <div className="mb-2 flex items-center gap-2">
        <span className="text-sm font-semibold text-stone-700 dark:text-slate-300">View content at ref:</span>
        <input value={viewRef} onChange={(e) => setViewRef(e.target.value)} className={`${INPUT} w-32`} />
        <button
          onClick={handleView}
          className="rounded-md bg-stone-200 px-3 py-1.5 text-sm font-medium text-stone-800 transition hover:bg-stone-300 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          View
        </button>
      </div>
      {viewedContent !== null && (
        <pre className="whitespace-pre-wrap rounded-md bg-stone-100 p-2 text-xs text-stone-800 dark:bg-slate-950 dark:text-slate-300">
          {viewedContent}
        </pre>
      )}

      {status && <p className="mt-2 text-sm text-stone-600 dark:text-slate-400">{status}</p>}
    </Card>
  )
}

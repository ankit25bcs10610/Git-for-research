import { useEffect, useState } from 'react'
import {
  createCodebaseBranch,
  createCodebaseCommit,
  getCodebaseContent,
  listCodebaseBranches,
  type Branch,
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
const BUTTON =
  'rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-stone-700 dark:bg-cyan-500 dark:text-slate-950 dark:hover:bg-cyan-400'

export default function CodebaseBranchesPanel({ artifactId, refreshSignal, onChanged }: Props) {
  const { profile } = useProfile()
  const [branches, setBranches] = useState<Branch[]>([])
  const [newBranchName, setNewBranchName] = useState('')
  const [newBranchFrom, setNewBranchFrom] = useState('master')

  const [viewRef, setViewRef] = useState('master')
  const [files, setFiles] = useState<Record<string, string> | null>(null)
  const [selectedPath, setSelectedPath] = useState<string | null>(null)

  const [commitBranch, setCommitBranch] = useState('master')
  const [commitPath, setCommitPath] = useState('')
  const [commitContent, setCommitContent] = useState('')
  const [commitMessage, setCommitMessage] = useState('')

  const [status, setStatus] = useState('')

  function refresh() {
    listCodebaseBranches(artifactId)
      .then(setBranches)
      .catch((err) => setStatus((err as Error).message))
  }

  useEffect(() => {
    refresh()
    setFiles(null)
    setSelectedPath(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifactId, refreshSignal])

  async function handleCreateBranch(e: React.FormEvent) {
    e.preventDefault()
    try {
      await createCodebaseBranch(artifactId, newBranchName, newBranchFrom)
      setStatus(`Created branch "${newBranchName}" from ${newBranchFrom}`)
      setNewBranchName('')
      refresh()
      onChanged()
    } catch (err) {
      setStatus((err as Error).message)
    }
  }

  async function handleView() {
    try {
      const { files } = await getCodebaseContent(artifactId, viewRef)
      setFiles(files)
      setSelectedPath(Object.keys(files)[0] ?? null)
    } catch (err) {
      setStatus((err as Error).message)
      setFiles(null)
    }
  }

  async function handleCommit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const result = await createCodebaseCommit(
        artifactId,
        commitBranch,
        { [commitPath]: commitContent },
        commitMessage,
        profile?.username ?? '',
      )
      setStatus(`Committed ${result.commit_ref} on ${result.branch_name}`)
      setCommitMessage('')
      refresh()
      onChanged()
    } catch (err) {
      setStatus((err as Error).message)
    }
  }

  return (
    <Card title="Codebase: branches, files, and commits">
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
          placeholder="master"
          value={newBranchFrom}
          onChange={(e) => setNewBranchFrom(e.target.value)}
          className={`${INPUT} w-24`}
        />
        <button type="submit" className={BUTTON}>
          Create
        </button>
      </form>

      <div className="mb-3 border-t border-stone-200 pt-3 dark:border-slate-800">
        <div className="mb-2 flex items-center gap-2">
          <span className="text-sm font-semibold text-stone-700 dark:text-slate-300">Browse files at ref:</span>
          <input value={viewRef} onChange={(e) => setViewRef(e.target.value)} className={`${INPUT} w-32`} />
          <button onClick={handleView} className={BUTTON}>
            Load
          </button>
        </div>
        {files && (
          <div className="flex gap-3">
            <ul className="w-1/3 max-h-56 space-y-0.5 overflow-y-auto font-mono text-xs">
              {Object.keys(files).map((path) => (
                <li key={path}>
                  <button
                    onClick={() => setSelectedPath(path)}
                    className={`w-full truncate rounded px-1.5 py-0.5 text-left transition ${
                      path === selectedPath
                        ? 'bg-stone-900 text-white dark:bg-cyan-500/20 dark:text-cyan-100'
                        : 'hover:bg-stone-100 dark:hover:bg-slate-800/60'
                    }`}
                  >
                    {path}
                  </button>
                </li>
              ))}
              {Object.keys(files).length === 0 && <li className="italic opacity-60">(empty)</li>}
            </ul>
            <pre className="max-h-56 flex-1 overflow-auto rounded-md bg-stone-100 p-2 text-xs text-stone-800 dark:bg-slate-950 dark:text-slate-300">
              {selectedPath ? files[selectedPath] : ''}
            </pre>
          </div>
        )}
      </div>

      <form onSubmit={handleCommit} className="space-y-2 border-t border-stone-200 pt-3 dark:border-slate-800">
        <p className="text-sm font-semibold text-stone-700 dark:text-slate-300">
          Add or update one file (deletions aren't supported via this form)
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-stone-600 dark:text-slate-400">onto branch</span>
          <input value={commitBranch} onChange={(e) => setCommitBranch(e.target.value)} className={`${INPUT} w-28`} />
          <input
            placeholder="file path, e.g. src/util.py"
            value={commitPath}
            onChange={(e) => setCommitPath(e.target.value)}
            required
            className={`${INPUT} flex-1`}
          />
          <input
            placeholder="commit message"
            value={commitMessage}
            onChange={(e) => setCommitMessage(e.target.value)}
            required
            className={`${INPUT} flex-1`}
          />
        </div>
        <textarea
          placeholder="new full content for this file"
          value={commitContent}
          onChange={(e) => setCommitContent(e.target.value)}
          required
          rows={5}
          className={`${INPUT} w-full font-mono`}
        />
        <button type="submit" className={BUTTON}>
          Commit
        </button>
      </form>

      {status && <p className="mt-2 text-sm text-stone-600 dark:text-slate-400">{status}</p>}
    </Card>
  )
}

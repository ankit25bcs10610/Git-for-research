import { useState } from 'react'
import { agentEdit } from '../api'
import { useProfile } from '../profile/ProfileContext'
import Card from './ui/Card'

interface Props {
  artifactId: string
  onChanged: () => void
}

const INPUT =
  'rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'

export default function AgentEditPanel({ artifactId, onChanged }: Props) {
  const { profile } = useProfile()
  const [baseBranch, setBaseBranch] = useState('main')
  const [instruction, setInstruction] = useState('')
  const [proposedContent, setProposedContent] = useState('')
  const [status, setStatus] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      const { merge_request_id } = await agentEdit(
        artifactId,
        baseBranch,
        instruction,
        proposedContent,
        profile?.username ?? '',
      )
      setStatus(
        `Agent opened merge request ${merge_request_id} — review and merge it in the "Merge requests" panel above.`,
      )
      setInstruction('')
      setProposedContent('')
      onChanged()
    } catch (err) {
      setStatus((err as Error).message)
    }
  }

  return (
    <Card title="7. Simulate an LLM agent edit (multi-agent editing)">
      <p className="mb-2 text-sm text-stone-600 dark:text-slate-400">
        No hosted LLM call happens here — this simulates an agent that already generated a proposed edit,
        opens its own branch off <code className="rounded bg-stone-200 px-1 dark:bg-slate-800">base_branch</code>,
        commits the proposal there, and opens a merge request back for a human to review.
      </p>
      <form onSubmit={handleSubmit} className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-stone-700 dark:text-slate-300">Base branch:</span>
          <input value={baseBranch} onChange={(e) => setBaseBranch(e.target.value)} className={`${INPUT} w-32`} />
        </div>
        <input
          placeholder="instruction given to the agent"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          required
          className={`${INPUT} w-full`}
        />
        <textarea
          placeholder="proposed full content (what the agent 'wrote')"
          value={proposedContent}
          onChange={(e) => setProposedContent(e.target.value)}
          required
          rows={4}
          className={`${INPUT} w-full font-mono`}
        />
        <button
          type="submit"
          className="rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-stone-700 dark:bg-cyan-500 dark:text-slate-950 dark:hover:bg-cyan-400"
        >
          Submit agent edit
        </button>
      </form>
      {status && <p className="mt-2 text-sm text-stone-600 dark:text-slate-400">{status}</p>}
    </Card>
  )
}

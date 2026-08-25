import { useState } from 'react'
import { getAnswer, search, type SearchResult } from '../api'
import Card from './ui/Card'

const INPUT =
  'rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'

export default function SearchPanel() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[] | null>(null)
  const [answer, setAnswer] = useState<string | null>(null)
  const [status, setStatus] = useState('')
  const [asking, setAsking] = useState(false)

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setAnswer(null)
    try {
      const r = await search(query)
      setResults(r)
      setStatus('')
    } catch (err) {
      setStatus((err as Error).message)
      setResults(null)
    }
  }

  async function handleAskAi() {
    setAsking(true)
    setStatus('')
    try {
      const r = await getAnswer(query)
      setAnswer(r.answer)
      setResults(r.sources)
    } catch (err) {
      setStatus((err as Error).message)
      setAnswer(null)
    } finally {
      setAsking(false)
    }
  }

  return (
    <Card title="8. Search across everything ingested (semantic retrieval)">
      <form onSubmit={handleSearch} className="mb-2 flex items-center gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="ask a question about your ingested research"
          required
          className={`${INPUT} flex-1`}
        />
        <button
          type="submit"
          className="rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-stone-700 dark:bg-cyan-500 dark:text-slate-950 dark:hover:bg-cyan-400"
        >
          Search
        </button>
      </form>
      <div className="mb-3 flex items-center gap-2">
        <button
          onClick={handleAskAi}
          disabled={!query || asking}
          className="rounded-md border border-violet-300 bg-violet-50 px-3 py-1.5 text-xs font-medium text-violet-700 transition hover:bg-violet-100 disabled:opacity-50 dark:border-violet-800 dark:bg-violet-500/10 dark:text-violet-300 dark:hover:bg-violet-500/20"
        >
          {asking ? 'Asking…' : 'Ask AI for a synthesized answer'}
        </button>
        <span className="text-xs text-stone-500 dark:text-slate-500">
          uses Groq (external API) — search above stays 100% local
        </span>
      </div>
      {status && <p className="text-sm text-rose-600 dark:text-rose-400">{status}</p>}
      {answer && (
        <div className="mb-3 rounded-md border border-violet-200 bg-violet-50/60 p-3 text-sm text-stone-800 dark:border-violet-900/50 dark:bg-violet-500/10 dark:text-slate-200">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-violet-700 dark:text-violet-400">
            AI-synthesized answer (Groq)
          </p>
          <p className="whitespace-pre-wrap">{answer}</p>
        </div>
      )}
      {results && (
        <ul className="space-y-2">
          {results.map((r) => (
            <li key={r.chunk_id} className="rounded-md border border-stone-200 p-2 text-sm dark:border-slate-800">
              <p className="text-stone-800 dark:text-slate-200">{r.text}</p>
              <p className="mt-1 font-mono text-xs opacity-60">
                score={r.score.toFixed(3)} · artifact={r.artifact_id.slice(0, 8)} · commit={r.commit_ref.slice(0, 8)}
              </p>
            </li>
          ))}
          {results.length === 0 && <p className="text-sm text-stone-500 dark:text-slate-400">No results.</p>}
        </ul>
      )}
    </Card>
  )
}

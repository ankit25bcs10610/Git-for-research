import { useState } from 'react'
import { search, type SearchResult } from '../api'
import Card from './ui/Card'

const INPUT =
  'rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'

export default function SearchPanel() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[] | null>(null)
  const [status, setStatus] = useState('')

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    try {
      const r = await search(query)
      setResults(r)
      setStatus('')
    } catch (err) {
      setStatus((err as Error).message)
      setResults(null)
    }
  }

  return (
    <Card title="8. Search across everything ingested (semantic retrieval)">
      <form onSubmit={handleSearch} className="mb-3 flex items-center gap-2">
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
      {status && <p className="text-sm text-rose-600 dark:text-rose-400">{status}</p>}
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

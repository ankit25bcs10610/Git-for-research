import { motion } from 'framer-motion'

interface TechItem {
  title: string
  description: string
  status: 'working' | 'gap'
}

const ITEMS: TechItem[] = [
  {
    title: 'Content-addressed commits, not a real git repo',
    description:
      "Every commit's text is stored as a SHA-256 content-addressed blob, deduplicated by hash, with commit rows carrying parent_ids, author, message, and timestamp; branches are named pointers to a head commit. It borrows git's vocabulary, but it's a custom SQL-backed model, not an actual git repository: commit IDs are random UUIDs (not content hashes), and there's no working tree or index.",
    status: 'working',
  },
  {
    title: 'Paragraph-level diff, and merge conflicts are chat-aware',
    description:
      'Diffs and merges both use whichever tokenizer matches the artifact — paragraphs for docs, one token per message for chat — via SequenceMatcher plus nested word-level diffing and a real diff3-style three-way comparison. A conflicting chat merge surfaces one conflict per message, not one conflict spanning the whole conversation.',
    status: 'working',
  },
  {
    title: 'Ingestion: one artifact per document, one artifact per conversation',
    description:
      'Markdown and PDF each become the first commit of exactly one new artifact. ChatGPT and Claude exports are walked conversation-by-conversation, creating one artifact per conversation in a single ingest call. PDF extraction is page-by-page text (no OCR, so scanned PDFs come out empty).',
    status: 'working',
  },
  {
    title: 'Codebase artifacts: real git repos, wired end-to-end',
    description:
      'A zip upload is unpacked into an actual git repository on disk (pygit2), tree-sitter-chunked function-by-function for semantic search, and exposed over its own branch/commit/diff/merge-request routes with file-path-level conflicts — a second, git-native versioning engine alongside the Postgres-backed one docs and chat use, not a reuse of it.',
    status: 'working',
  },
  {
    title: 'Local semantic search by default; an AI answer is opt-in',
    description:
      "Artifacts are chunked (by paragraph, or by message for chat) and embedded locally with sentence-transformers' all-MiniLM-L6-v2 — no network call, no third-party API, and this is what plain Search always uses. A separate \"Ask AI\" button additionally sends the retrieved excerpts to Groq to synthesize a cited natural-language answer — that one action is the only place this app calls an external LLM, and it's disabled entirely if no Groq API key is configured.",
    status: 'working',
  },
  {
    title: 'Merge requests and "agent edit", honestly scoped',
    description:
      'A merge request computes the common-ancestor diff and either auto-merges cleanly or blocks on conflicts until every conflicting position is resolved. The /agent-edit endpoint is named for future LLM integration but today just takes text you already generated, opens a branch, commits it, and files a merge request — it does not call any model itself.',
    status: 'working',
  },
  {
    title: 'Real-time CRDT co-editing, now wired to real commits',
    description:
      'A y-websocket relay syncs a shared Yjs document per artifact+branch across every open tab in real time. A "commit this as a snapshot" action turns the current live text into a real, versioned commit via the same DAG the rest of the app uses — the relay, the sync, and the commit bridge are all exercised together, not just unit-tested in isolation.',
    status: 'working',
  },
]

const STATUS_LABEL: Record<TechItem['status'], string> = {
  working: 'Working',
  gap: 'Known gap',
}

const STATUS_CLASSES: Record<TechItem['status'], string> = {
  working:
    'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400',
  gap: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
}

export default function DeepTech() {
  return (
    <section className="mx-auto mb-6 max-w-4xl rounded-xl border border-stone-200/70 bg-white/70 p-5 shadow-sm backdrop-blur-md dark:border-slate-800/70 dark:bg-slate-900/50">
      <h2 className="mb-1 text-lg font-semibold text-stone-900 dark:text-slate-100">Under the hood</h2>
      <p className="mb-4 text-sm text-stone-600 dark:text-slate-400">
        What's actually implemented today, stated plainly — including the rough edges.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {ITEMS.map((item, i) => (
          <motion.div
            key={item.title}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: i * 0.05 }}
            className="rounded-lg border border-stone-200/70 bg-white/60 p-3 dark:border-slate-800/60 dark:bg-slate-950/40"
          >
            <div className="mb-1 flex items-start justify-between gap-2">
              <p className="text-sm font-semibold text-stone-800 dark:text-cyan-300">{item.title}</p>
              <span
                className={`shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${STATUS_CLASSES[item.status]}`}
              >
                {STATUS_LABEL[item.status]}
              </span>
            </div>
            <p className="text-xs leading-relaxed text-stone-600 dark:text-slate-400">{item.description}</p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}

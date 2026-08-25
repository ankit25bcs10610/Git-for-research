import { motion } from 'framer-motion'

interface Step {
  step: number
  title: string
  description: string
}

const STEPS: Step[] = [
  {
    step: 1,
    title: 'Ingest an artifact',
    description:
      'Set a workspace ID (defaults to demo-workspace), pick a kind — Markdown, ChatGPT export, Claude export, or PDF — choose a file, and ingest it. Markdown and PDF each produce exactly one new artifact, committed as the first commit on its own main branch and indexed for search automatically. ChatGPT and Claude exports are handled per conversation: the app parses every conversation in the export and creates one artifact per conversation in the same step.',
  },
  {
    step: 2,
    title: 'Select an artifact',
    description:
      "Only the first artifact from your last ingest is auto-selected, loading its commit graph, branches, and content. For a multi-conversation export, every other conversation is created too and appears in the workspace's artifact list — open the list and pick any of them to switch to it.",
  },
  {
    step: 3,
    title: 'Explore the commit graph',
    description:
      'The selected artifact\'s history renders as a 3D scene — commits as spheres laid out by branch and depth. Drag to orbit, scroll to zoom, hover a commit for its ID/message/author, or click one to load its raw content below.',
  },
  {
    step: 4,
    title: 'Branch and commit',
    description:
      'Create a new branch from any ref, commit new full content to a branch with a message, and view the raw text at any ref or commit — clicking a commit in the graph loads its content here automatically.',
  },
  {
    step: 5,
    title: 'Diff two refs',
    description:
      'Compare any two refs and see a breakdown by paragraph (for docs) or by message (for chat) — added/removed/changed/unchanged — with word-level highlighting inside changed entries.',
  },
  {
    step: 6,
    title: 'Open and resolve a merge request',
    description:
      'Open a merge request between two branches and review its diff. If content conflicts, the merge is blocked until you submit a resolution for every conflicting position; a clean merge produces a real two-parent commit. For chat artifacts, conflict detection currently treats the whole conversation as a single position rather than per message — a known granularity gap, not a bug in the merge logic itself.',
  },
  {
    step: 7,
    title: 'Search across everything ingested',
    description:
      'Type a query to run local semantic search over every indexed chunk; each result shows its score, source artifact, and the exact commit it came from.',
  },
]

export default function HowToUse() {
  return (
    <section className="mx-auto mb-6 max-w-4xl rounded-xl border border-stone-200/70 bg-white/70 p-5 shadow-sm backdrop-blur-md dark:border-slate-800/70 dark:bg-slate-900/50">
      <h2 className="mb-1 text-lg font-semibold text-stone-900 dark:text-slate-100">How it works</h2>
      <p className="mb-4 text-sm text-stone-600 dark:text-slate-400">
        The real, current flow through this app — every step below matches the actual UI, not an aspiration.
      </p>
      <ol className="relative space-y-3">
        <div
          aria-hidden="true"
          className="absolute bottom-6 left-3 top-6 w-px bg-gradient-to-b from-stone-300 via-stone-300 to-transparent dark:from-cyan-500/40 dark:via-violet-500/40"
        />
        {STEPS.map((s, i) => (
          <motion.li
            key={s.step}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: i * 0.04 }}
            className="relative flex gap-3"
          >
            <span className="relative z-10 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-stone-900 text-xs font-semibold text-white dark:bg-gradient-to-br dark:from-cyan-400 dark:to-violet-500 dark:text-slate-950">
              {s.step}
            </span>
            <div>
              <p className="text-sm font-semibold text-stone-800 dark:text-slate-200">{s.title}</p>
              <p className="text-sm text-stone-600 dark:text-slate-400">{s.description}</p>
            </div>
          </motion.li>
        ))}
      </ol>
    </section>
  )
}

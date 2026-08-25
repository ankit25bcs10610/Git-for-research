import { motion } from 'framer-motion'
import HowToUse from './HowToUse'
import DeepTech from './DeepTech'

interface Props {
  onStart: () => void
}

const TRUST_BADGES = [
  'Local semantic search',
  'External LLM calls are opt-in',
  'pgvector semantic search',
  'Real two-parent merges',
]

function StartButton({ onStart, className = '' }: { onStart: () => void; className?: string }) {
  return (
    <motion.button
      onClick={onStart}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.98 }}
      className={`group inline-flex items-center gap-2 rounded-full bg-stone-900 px-6 py-3 text-base font-semibold text-white shadow-lg transition-colors hover:bg-stone-700 dark:bg-gradient-to-r dark:from-cyan-400 dark:to-violet-500 dark:text-slate-950 dark:hover:from-cyan-300 dark:hover:to-violet-400 ${className}`}
    >
      Let's start using this
      <span className="transition-transform group-hover:translate-x-1">→</span>
    </motion.button>
  )
}

export default function LandingPage({ onStart }: Props) {
  return (
    <div>
      <section className="mx-auto flex min-h-[75vh] max-w-3xl flex-col items-center justify-center px-4 text-center">
        <motion.h1
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="bg-gradient-to-r from-stone-900 to-stone-600 bg-clip-text text-5xl font-bold tracking-tight text-transparent dark:from-cyan-300 dark:to-violet-400 md:text-6xl"
        >
          Git for Research
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mt-4 text-lg font-medium text-stone-800 dark:text-slate-200"
        >
          Git for your research: version, diff, and merge chats and documents, not just code.
        </motion.p>
        <motion.p
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-3 max-w-xl text-sm text-stone-600 dark:text-slate-400"
        >
          Ingest a chat export, a PDF, or a markdown note — each conversation or document lands as a real
          commit — then branch, diff, and merge across everything you've imported and search it semantically,
          all running locally.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.25 }}
          className="mt-6 flex flex-wrap items-center justify-center gap-2"
        >
          {TRUST_BADGES.map((badge) => (
            <span
              key={badge}
              className="rounded-full border border-stone-300/70 bg-white/50 px-3 py-1 text-xs font-medium text-stone-600 backdrop-blur-sm dark:border-slate-700/70 dark:bg-slate-900/40 dark:text-slate-400"
            >
              {badge}
            </span>
          ))}
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.35 }}
          className="mt-8"
        >
          <StartButton onStart={onStart} />
        </motion.div>
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
          className="mt-10 text-stone-400 dark:text-slate-600"
          aria-hidden="true"
        >
          ↓ scroll to see how it works
        </motion.div>
      </section>

      <HowToUse />
      <DeepTech />

      <div className="mx-auto mb-10 max-w-4xl text-center">
        <StartButton onStart={onStart} />
      </div>
    </div>
  )
}

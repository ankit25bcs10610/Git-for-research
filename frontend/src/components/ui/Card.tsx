import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

interface Props {
  title: ReactNode
  children: ReactNode
  className?: string
}

export default function Card({ title, children, className = '' }: Props) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className={`rounded-xl border border-stone-200/70 bg-white/70 p-5 shadow-sm backdrop-blur-md transition-colors dark:border-slate-800/70 dark:bg-slate-900/50 dark:shadow-none ${className}`}
    >
      <h2 className="mb-3 text-base font-semibold text-stone-900 dark:text-slate-100">{title}</h2>
      {children}
    </motion.section>
  )
}

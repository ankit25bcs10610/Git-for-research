import { motion } from 'motion/react'
import { SectionEyebrow } from './primitives'

const chips = ['Auto-categorize', 'Snooze for later', 'Silent newsletters', 'One-tap unsubscribe']

const categories = [
  {
    name: 'Priority',
    color: '#ffffff',
    count: 4,
    items: ['Sophia Chen — Q3 review', 'David Lim — contract signoff'],
  },
  {
    name: 'Follow-up',
    color: '#e5e5e5',
    count: 7,
    items: ['Marcus — design review', 'Figma — comment thread'],
  },
  {
    name: 'Updates',
    color: '#a3a3a3',
    count: 18,
    items: ['Vercel — deploy ready', 'GitHub — PR #482 merged'],
  },
  {
    name: 'Archived',
    color: '#525252',
    count: 13,
    items: ['Stripe payout · Newsletter · Receipts'],
  },
]

export default function FeatureTriage() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-20 md:py-28">
      <div className="grid md:grid-cols-2 gap-10 md:gap-16 items-start">
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.7 }}
        >
          <SectionEyebrow label="Triage" tag="AI-native" />
          <h2 className="mt-5 text-3xl md:text-5xl font-semibold tracking-tight leading-[1.02]">
            Clear your inbox
            <br />
            in a single pass.
          </h2>
          <p className="mt-6 text-white/60 text-base leading-[1.6] max-w-md">
            Aura reads every message, understands intent, and routes the noise away from the
            signal. Focus on what moves your day forward — the rest handles itself.
          </p>
          <div className="flex flex-wrap gap-2 mt-6">
            {chips.map((chip) => (
              <span
                key={chip}
                className="text-xs text-white/70 px-3 py-1.5 rounded-full border border-white/10 bg-white/[0.03]"
              >
                {chip}
              </span>
            ))}
          </div>
        </motion.div>

        <div className="liquid-glass rounded-2xl p-5">
          <div className="text-xs text-white/50 mb-4">Today · 42 messages triaged</div>
          <div className="space-y-3">
            {categories.map((category) => (
              <div key={category.name} className="liquid-glass rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-1.5 h-1.5 rounded-full"
                      style={{ backgroundColor: category.color }}
                    />
                    <span className="text-sm text-white/80">{category.name}</span>
                  </div>
                  <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/70">
                    {category.count}
                  </span>
                </div>
                <div className="mt-2 space-y-1">
                  {category.items.map((item) => (
                    <div key={item} className="text-white/50 text-xs">
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

import { motion } from 'motion/react'
import { ChevronRight } from 'lucide-react'
import { AppleButton } from './primitives'

export default function FinalCTA({ onOpenWaitlist }: { onOpenWaitlist: (source: 'download' | 'sales') => void }) {
  return (
    <section className="max-w-6xl mx-auto px-6 py-20 md:py-32">
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.7 }}
        className="liquid-glass relative overflow-hidden rounded-3xl px-8 py-16 md:py-24 text-center"
      >
        <div
          className="absolute inset-0 z-0 pointer-events-none"
          style={{
            background:
              'radial-gradient(600px circle at 50% 0%, rgba(255,255,255,0.15), transparent 70%)',
            opacity: 0.3,
          }}
        />
        <div className="relative z-10">
          <h2 className="text-4xl md:text-6xl font-semibold tracking-tight leading-[1.02]">
            Close the tabs.
            <br />
            Open your day.
          </h2>
          <p className="mt-6 text-white/60 max-w-md mx-auto text-sm leading-[1.6]">
            Join thousands of builders, founders, and operators who treat email like a tool — not
            an obligation.
          </p>
          <div className="flex items-center justify-center gap-4 mt-8">
            <AppleButton label="Download Aura" onClick={() => onOpenWaitlist('download')} />
            <button
              onClick={() => onOpenWaitlist('sales')}
              className="rounded-full border border-white/15 text-white text-sm font-medium px-5 py-3 hover:bg-white/5"
            >
              Talk to sales
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </motion.div>
    </section>
  )
}

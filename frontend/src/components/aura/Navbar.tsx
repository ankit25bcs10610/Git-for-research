import { useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { Menu, X } from 'lucide-react'
import { AppleButton, LogoMark } from './primitives'

// Only "Solutions" and "Pricing" map to a real section on this single page.
// Blog/Documentation/Careers have no destination (no such pages exist) --
// they're kept as inert links rather than faked, same as most real landing
// pages before those pages are built.
const NAV_LINKS: { label: string; href: string }[] = [
  { label: 'Solutions', href: '#solutions' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'Blog', href: '#' },
  { label: 'Documentation', href: '#' },
  { label: 'Careers', href: '#' },
]

export default function Navbar({ onOpenWaitlist }: { onOpenWaitlist: () => void }) {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <motion.nav
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className="relative max-w-6xl mx-auto px-6 flex items-center justify-between py-6"
    >
      <LogoMark className="w-8 h-8" />

      <nav className="hidden md:flex gap-8">
        {NAV_LINKS.map(({ label, href }, i) => (
          <motion.a
            key={label}
            href={href}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.05, duration: 0.5 }}
            className="text-white/70 text-sm font-medium hover:text-white"
          >
            {label}
          </motion.a>
        ))}
      </nav>

      <div className="hidden md:block">
        <AppleButton label="Downloada" onClick={onOpenWaitlist} />
      </div>

      <button
        onClick={() => setMobileOpen((open) => !open)}
        aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
        className="md:hidden w-10 h-10 rounded-full border border-white/10 bg-white/5 flex items-center justify-center"
      >
        {mobileOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
      </button>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="liquid-glass absolute top-full left-6 right-6 mt-2 rounded-2xl p-4 flex flex-col gap-1 md:hidden z-20"
          >
            {NAV_LINKS.map(({ label, href }) => (
              <a
                key={label}
                href={href}
                onClick={() => setMobileOpen(false)}
                className="text-white/70 text-sm font-medium hover:text-white px-3 py-2 rounded-lg hover:bg-white/5"
              >
                {label}
              </a>
            ))}
            <div className="mt-2">
              <AppleButton
                label="Downloada"
                full
                onClick={() => {
                  setMobileOpen(false)
                  onOpenWaitlist()
                }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  )
}

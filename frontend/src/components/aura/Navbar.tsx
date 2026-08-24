import { motion } from 'motion/react'
import { Menu } from 'lucide-react'
import { AppleButton, LogoMark } from './primitives'

const NAV_LINKS = ['Solutions', 'Pricing', 'Blog', 'Documentation', 'Careers']

export default function Navbar() {
  return (
    <motion.nav
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className="max-w-6xl mx-auto px-6 flex items-center justify-between py-6"
    >
      <LogoMark className="w-8 h-8" />

      <nav className="hidden md:flex gap-8">
        {NAV_LINKS.map((label, i) => (
          <motion.a
            key={label}
            href="#"
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
        <AppleButton label="Downloada" />
      </div>

      <button className="md:hidden w-10 h-10 rounded-full border border-white/10 bg-white/5 flex items-center justify-center">
        <Menu className="w-4 h-4" />
      </button>
    </motion.nav>
  )
}

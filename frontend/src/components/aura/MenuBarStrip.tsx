import { motion } from 'motion/react'
import { Search } from 'lucide-react'
import { AppleLogo } from './primitives'

const menuItems = ['File', 'Edit', 'View', 'Go', 'Window', 'Help']

export default function MenuBarStrip() {
  return (
    <motion.div
      className="h-10 bg-black/40 backdrop-blur-md border-t border-b border-white/10"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, delay: 0.9 }}
    >
      <div className="max-w-6xl mx-auto px-6 h-full flex items-center justify-between text-xs">
        <div className="flex items-center gap-4">
          <AppleLogo className="w-3.5 h-3.5" />
          <span className="font-bold text-white">Aura</span>
          {menuItems.map((item, index) => (
            <span
              key={item}
              className={`text-white/60 hover:text-white cursor-default ${
                index > 3 ? 'hidden md:inline' : index > 2 ? 'hidden sm:inline' : ''
              }`}
            >
              {item}
            </span>
          ))}
        </div>
        <div className="flex items-center gap-4">
          <Search className="w-3.5 h-3.5" />
          <span>Wed May 6 1:09 PM</span>
        </div>
      </div>
    </motion.div>
  )
}

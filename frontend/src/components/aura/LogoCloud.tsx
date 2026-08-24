import { motion } from 'motion/react'

const LOGOS = ['Linear', 'Vercel', 'Figma', 'Stripe', 'Ramp', 'Notion', 'Loom', 'Arc']

export default function LogoCloud() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-16 md:py-20">
      <p className="text-xs uppercase tracking-widest text-white/40 text-center">
        Trusted by the world's most thoughtful teams
      </p>
      <div className="mt-10 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-6">
        {LOGOS.map((name, i) => (
          <motion.div
            key={name}
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.05 }}
            className="text-sm font-semibold tracking-tight text-white/50 hover:text-white text-center"
          >
            {name}
          </motion.div>
        ))}
      </div>
    </section>
  )
}

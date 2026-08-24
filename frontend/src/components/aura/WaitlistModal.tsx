import { useState, type FormEvent } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { X } from 'lucide-react'
import { supabase, supabaseConfigured } from '../../lib/supabase'

export interface WaitlistContext {
  source: 'download' | 'plan' | 'sales'
  plan?: string
}

interface WaitlistModalProps {
  context: WaitlistContext | null
  onClose: () => void
}

const COPY: Record<WaitlistContext['source'], { title: string; body: string }> = {
  download: {
    title: 'Get Aura',
    body: "Aura isn't publicly downloadable yet. Leave your email and we'll notify you the moment it ships.",
  },
  plan: {
    title: 'Join the waitlist',
    body: "We'll email you as soon as this plan is open for signups.",
  },
  sales: {
    title: 'Talk to sales',
    body: "Leave your email and someone from our team will reach out.",
  },
}

export default function WaitlistModal({ context, onClose }: WaitlistModalProps) {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  if (!context) return null
  const activeContext: WaitlistContext = context

  const copy = COPY[activeContext.source]

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()

    if (!supabaseConfigured || !supabase) {
      setStatus('error')
      setErrorMessage(
        'Waitlist signup is not connected yet -- this needs a Supabase project URL and anon key (see frontend/.env.example).'
      )
      return
    }

    setStatus('submitting')
    setErrorMessage('')

    const { error } = await supabase.from('waitlist').insert({
      email,
      source: activeContext.source,
      plan: activeContext.plan ?? null,
    })

    if (error) {
      setStatus('error')
      setErrorMessage(error.message)
      return
    }

    setStatus('success')
  }

  function handleClose() {
    setEmail('')
    setStatus('idle')
    setErrorMessage('')
    onClose()
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-6"
        onClick={handleClose}
      >
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.98 }}
          transition={{ duration: 0.2 }}
          onClick={(e) => e.stopPropagation()}
          className="liquid-glass relative w-full max-w-sm rounded-2xl bg-[#0e1014] p-6"
        >
          <button
            onClick={handleClose}
            aria-label="Close"
            className="absolute top-4 right-4 w-8 h-8 rounded-full border border-white/10 bg-white/5 flex items-center justify-center hover:bg-white/10"
          >
            <X className="w-4 h-4" />
          </button>

          {status === 'success' ? (
            <div className="py-4">
              <h3 className="text-xl font-semibold">You're on the list.</h3>
              <p className="mt-2 text-sm text-white/60">We'll email {email} as soon as there's news.</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <h3 className="text-xl font-semibold pr-8">{copy.title}</h3>
              <p className="mt-2 text-sm text-white/60">{copy.body}</p>
              {context.plan && (
                <p className="mt-2 text-xs text-white/40">Plan: {context.plan}</p>
              )}
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="mt-4 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-white/30"
              />
              {status === 'error' && (
                <p className="mt-2 text-xs text-red-400">{errorMessage}</p>
              )}
              <button
                type="submit"
                disabled={status === 'submitting'}
                className="mt-4 w-full rounded-full bg-white text-black font-medium text-sm px-5 py-3 hover:bg-white/90 active:scale-[0.98] disabled:opacity-50"
              >
                {status === 'submitting' ? 'Submitting…' : 'Notify me'}
              </button>
            </form>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

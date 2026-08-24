const TESTIMONIALS = [
  {
    quote:
      'Aura gave our leadership team four hours of their week back. It reads like email from the future.',
    name: 'Parker Wilf',
    role: 'Group Product Manager',
    company: 'MERCURY',
  },
  {
    quote:
      "The command palette alone has changed how I process messages. I can't imagine going back to a traditional client.",
    name: 'Andrew von Rosenbach',
    role: 'Senior Engineering Program Manager',
    company: 'COHERE',
  },
  {
    quote:
      'Triage that actually understands context. Our team stopped dreading Monday morning inboxes.',
    name: 'Mathies Christensen',
    role: 'Engineering Manager',
    company: 'LUNAR',
  },
]

export default function Testimonials() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-20 md:py-28 border-t border-white/10">
      <div className="grid md:grid-cols-3 gap-6">
        {TESTIMONIALS.map((t) => (
          <figure key={t.name} className="liquid-glass rounded-2xl p-6">
            <blockquote className="text-sm text-white/80 leading-[1.6]">
              "{t.quote}"
            </blockquote>
            <figcaption className="mt-6 pt-5 border-t border-white/10">
              <div className="text-sm font-semibold">{t.name}</div>
              <div className="text-xs text-white/50">{t.role}</div>
              <div className="text-xs text-white font-semibold tracking-wide">
                {t.company}
              </div>
            </figcaption>
          </figure>
        ))}
      </div>
    </section>
  )
}

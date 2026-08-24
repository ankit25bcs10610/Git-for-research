import { motion } from 'motion/react'
import {
  Sparkles,
  Inbox,
  Star,
  Send,
  FileText,
  Archive,
  Trash2,
  Search,
  Reply,
  Forward,
  MoreHorizontal,
  Paperclip,
} from 'lucide-react'

const navItems = [
  { icon: Inbox, label: 'Inbox', count: 12, active: true },
  { icon: Star, label: 'Starred', count: 3, active: false },
  { icon: Send, label: 'Sent', count: null, active: false },
  { icon: FileText, label: 'Drafts', count: 2, active: false },
  { icon: Archive, label: 'Archive', count: null, active: false },
  { icon: Trash2, label: 'Trash', count: null, active: false },
]

const labels = [
  { name: 'Work', color: '#00d2ff' },
  { name: 'Personal', color: '#A4F4FD' },
  { name: 'Travel', color: '#f59e0b' },
  { name: 'Finance', color: '#10b981' },
]

const messages = [
  {
    sender: 'Linear',
    subject: 'Weekly product digest',
    preview: 'Your team shipped 23 issues this week...',
    time: '9:41 AM',
    unread: true,
    active: true,
  },
  {
    sender: 'Sophia Chen',
    subject: 'Re: Q3 roadmap review',
    preview: 'Thanks for sending the deck over. I had a few thoughts...',
    time: '8:12 AM',
    unread: true,
    active: false,
  },
  {
    sender: 'Figma',
    subject: 'Marcus commented on your file',
    preview: 'Love the new direction on the landing hero.',
    time: 'Yesterday',
    unread: false,
    active: false,
  },
  {
    sender: 'Stripe',
    subject: 'Payout of $12,480.00 sent',
    preview: 'Your payout is on its way to your bank...',
    time: 'Yesterday',
    unread: false,
    active: false,
  },
  {
    sender: 'Vercel',
    subject: 'Deployment ready for aura-web',
    preview: 'Preview is live at aura-web-g3f.vercel.app',
    time: 'Mon',
    unread: false,
    active: false,
  },
  {
    sender: 'GitHub',
    subject: '[aura/core] PR #482 approved',
    preview: 'david-lim approved your pull request.',
    time: 'Mon',
    unread: false,
    active: false,
  },
]

const bodyParagraphs = [
  'Hi team,',
  'Here is your weekly digest of everything happening across your projects. This was a strong week with significant progress on the Q3 roadmap.',
  'Twenty-three issues were closed, fourteen pull requests were merged, and two customer-facing features went out. The velocity trend continues to climb.',
  'Let me know if you would like a deeper breakdown by project or contributor.',
]

export default function InboxMockup() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-16 md:py-24">
      <motion.div
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 1.1 }}
        className="relative rounded-2xl overflow-hidden border border-white/10 bg-[#0e1014]/90 backdrop-blur-2xl"
      >
        {/* Title bar */}
        <div className="relative flex items-center px-4 py-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#ff5f57' }} />
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#febc2e' }} />
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#28c840' }} />
          </div>
          <div className="absolute left-1/2 -translate-x-1/2 text-xs text-white/50">
            Aura — Inbox
          </div>
        </div>

        {/* Body */}
        <div className="grid grid-cols-12 h-[520px]">
          {/* Sidebar */}
          <div className="col-span-3 border-r border-white/10 bg-black/30 p-4">
            <button className="rounded-lg bg-white text-black text-xs font-semibold px-3 py-2 w-full flex items-center justify-center gap-2">
              <Sparkles className="w-3.5 h-3.5" />
              Compose with Aura
            </button>

            <div className="mt-4 flex flex-col gap-1">
              {navItems.map((item) => {
                const Icon = item.icon
                return (
                  <div
                    key={item.label}
                    className={`flex items-center justify-between rounded-md px-2 py-1.5 text-sm ${
                      item.active ? 'bg-white/10 text-white' : 'text-white/60 hover:bg-white/5'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Icon className="w-4 h-4" />
                      <span>{item.label}</span>
                    </div>
                    {item.count !== null && (
                      <span className="text-xs text-white/40">{item.count}</span>
                    )}
                  </div>
                )
              })}
            </div>

            <div className="text-xs uppercase tracking-wider text-white/40 mt-6 mb-2">
              Labels
            </div>
            <div className="flex flex-col gap-1">
              {labels.map((label) => (
                <div
                  key={label.name}
                  className="flex items-center gap-2 px-2 py-1.5 text-white/60 text-sm"
                >
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: label.color }}
                  />
                  <span>{label.name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Message list */}
          <div className="col-span-4 border-r border-white/10 flex flex-col">
            <div className="flex items-center gap-2 px-3 py-2 border-b border-white/10 text-white/40 text-sm">
              <Search className="w-4 h-4" />
              <span>Search mail</span>
            </div>
            <div className="overflow-y-auto flex-1">
              {messages.map((message) => (
                <div
                  key={message.subject}
                  className={`px-3 py-3 border-b border-white/5 ${
                    message.active ? 'bg-white/5' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      {message.unread && (
                        <span className="w-1.5 h-1.5 rounded-full bg-[#00d2ff]" />
                      )}
                      <span
                        className={`text-sm ${
                          message.unread ? 'font-semibold text-white' : 'text-white/60'
                        }`}
                      >
                        {message.sender}
                      </span>
                    </div>
                    <span className="text-xs text-white/40">{message.time}</span>
                  </div>
                  <div className="text-sm text-white/80 mt-0.5 truncate">{message.subject}</div>
                  <div className="text-xs text-white/40 mt-0.5 truncate">{message.preview}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Reader pane */}
          <div className="col-span-5 flex flex-col">
            <div className="flex items-center gap-1 px-3 py-2 border-b border-white/10">
              <button className="w-7 h-7 rounded-md hover:bg-white/5 flex items-center justify-center">
                <Reply className="w-4 h-4 text-white/60" />
              </button>
              <button className="w-7 h-7 rounded-md hover:bg-white/5 flex items-center justify-center">
                <Forward className="w-4 h-4 text-white/60" />
              </button>
              <button className="w-7 h-7 rounded-md hover:bg-white/5 flex items-center justify-center">
                <Archive className="w-4 h-4 text-white/60" />
              </button>
              <button className="w-7 h-7 rounded-md hover:bg-white/5 flex items-center justify-center">
                <Trash2 className="w-4 h-4 text-white/60" />
              </button>
              <div className="flex-1" />
              <button className="w-7 h-7 rounded-md hover:bg-white/5 flex items-center justify-center">
                <MoreHorizontal className="w-4 h-4 text-white/60" />
              </button>
            </div>

            <div className="px-5 pt-4 overflow-y-auto flex-1">
              <h3 className="text-white text-lg font-semibold">Weekly product digest</h3>
              <div className="flex items-center gap-2 mt-2">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#00d2ff] to-[#0B2551] flex items-center justify-center text-xs font-semibold">
                  L
                </div>
                <div className="flex flex-col leading-tight">
                  <span className="text-white text-sm font-semibold">Linear</span>
                  <span className="text-white/50 text-xs">to me · 9:41 AM</span>
                </div>
                <span className="rounded-full border border-white/10 px-2 py-0.5 text-xs text-white/60">
                  Work
                </span>
              </div>

              <div className="liquid-glass rounded-lg p-3 mt-4">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-3.5 h-3.5" style={{ color: '#A4F4FD' }} />
                  <span className="text-xs font-semibold text-white/70">Summary by Aura</span>
                </div>
                <p className="text-sm text-white/70 mt-2">
                  Your team closed 23 issues, merged 14 PRs, and shipped 2 features. Top
                  contributor: Marcus. No action needed.
                </p>
              </div>

              {bodyParagraphs.map((paragraph) => (
                <p key={paragraph} className="text-sm text-white/70 leading-[1.6] mt-4">
                  {paragraph}
                </p>
              ))}
              <p className="text-sm text-white/50 leading-[1.6] mt-4">— The Linear team</p>

              <div className="inline-flex items-center gap-2 mt-4 rounded-md border border-white/10 px-3 py-2 text-xs text-white/70 w-fit">
                <Paperclip className="w-3.5 h-3.5" />
                <span>digest-may-6.pdf</span>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

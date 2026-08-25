import { useEffect, useRef, useState } from 'react'
import * as Y from 'yjs'
import { WebsocketProvider } from 'y-websocket'
import { commitLiveSnapshot, CRDT_WS_URL } from '../api'
import { useProfile } from '../profile/ProfileContext'
import Card from './ui/Card'

interface Props {
  artifactId: string
  onCommitted: () => void
}

const INPUT =
  'rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'
const BUTTON =
  'rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-stone-700 dark:bg-cyan-500 dark:text-slate-950 dark:hover:bg-cyan-400'

// Applies a plain textarea's full-value change to a Yjs Text type as a
// minimal insert/delete at the common-prefix/suffix boundary, instead of
// replacing the whole string -- so two clients editing different parts of
// the same document merge character-by-character instead of one client's
// whole-document write clobbering the other's.
function applyTextDiff(ytext: Y.Text, oldText: string, newText: string) {
  if (oldText === newText) return
  let start = 0
  while (start < oldText.length && start < newText.length && oldText[start] === newText[start]) start++
  let oldEnd = oldText.length
  let newEnd = newText.length
  while (oldEnd > start && newEnd > start && oldText[oldEnd - 1] === newText[newEnd - 1]) {
    oldEnd--
    newEnd--
  }
  ytext.doc?.transact(() => {
    if (oldEnd > start) ytext.delete(start, oldEnd - start)
    if (newEnd > start) ytext.insert(start, newText.slice(start, newEnd))
  })
}

export default function LiveEditor({ artifactId, onCommitted }: Props) {
  const { profile } = useProfile()
  const [branchName, setBranchName] = useState('main')
  const [text, setText] = useState('')
  const [status, setStatus] = useState('connecting…')
  const [collaborators, setCollaborators] = useState(1)
  const [committing, setCommitting] = useState(false)

  const ytextRef = useRef<Y.Text | null>(null)

  useEffect(() => {
    const room = `${artifactId}__${branchName}`
    const doc = new Y.Doc()
    const provider = new WebsocketProvider(CRDT_WS_URL, room, doc)
    const ytext = doc.getText('content')
    ytextRef.current = ytext

    setStatus('connecting…')
    setText(ytext.toString())

    function onSync(isSynced: boolean) {
      setStatus(isSynced ? 'synced' : 'connecting…')
    }
    function onYText() {
      setText(ytext.toString())
    }
    function onAwarenessChange() {
      setCollaborators(provider.awareness.getStates().size)
    }

    provider.on('sync', onSync)
    ytext.observe(onYText)
    provider.awareness.on('change', onAwarenessChange)

    return () => {
      provider.awareness.off('change', onAwarenessChange)
      ytext.unobserve(onYText)
      provider.off('sync', onSync)
      provider.destroy()
      doc.destroy()
      ytextRef.current = null
    }
  }, [artifactId, branchName])

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const ytext = ytextRef.current
    if (!ytext) return
    applyTextDiff(ytext, ytext.toString(), e.target.value)
  }

  async function handleCommit() {
    setCommitting(true)
    setStatus('committing…')
    try {
      await commitLiveSnapshot(artifactId, branchName, profile?.username ?? '')
      setStatus('committed — see it in the commit graph above')
      onCommitted()
    } catch (err) {
      setStatus((err as Error).message)
    } finally {
      setCommitting(false)
    }
  }

  return (
    <Card title="Live co-editing (CRDT)">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-stone-700 dark:text-slate-300">Branch:</span>
        <input value={branchName} onChange={(e) => setBranchName(e.target.value)} className={`${INPUT} w-32`} />
        <span className="text-xs text-stone-500 dark:text-slate-500">
          {status} · {collaborators} tab{collaborators === 1 ? '' : 's'} connected
        </span>
      </div>
      <textarea
        value={text}
        onChange={handleChange}
        rows={8}
        placeholder="Type here — open this artifact in another browser tab to see it sync live."
        className={`${INPUT} w-full font-mono`}
      />
      <div className="mt-3 flex items-center gap-2">
        <button onClick={handleCommit} disabled={committing} className={`${BUTTON} disabled:opacity-50`}>
          {committing ? 'Committing…' : 'Commit this as a snapshot'}
        </button>
        <p className="text-xs text-stone-500 dark:text-slate-500">
          Turns the current live text into a real, versioned commit on this branch.
        </p>
      </div>
    </Card>
  )
}

import { useEffect, useState, type ReactNode } from 'react'
import { createUser, listUsers, type UserProfile } from '../api'
import { useProfile } from '../profile/ProfileContext'

const INPUT =
  'flex-1 rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 focus:border-cyan-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'

export default function ProfileGate({ children }: { children: ReactNode }) {
  const { profile, setProfile, clearProfile } = useProfile()
  const [users, setUsers] = useState<UserProfile[]>([])
  const [newUsername, setNewUsername] = useState('')
  const [status, setStatus] = useState('')

  useEffect(() => {
    listUsers()
      .then((fetched) => {
        setUsers(fetched)
        if (profile && !fetched.some((u) => u.username === profile.username)) {
          clearProfile()
        }
      })
      .catch((err) => setStatus((err as Error).message))
  }, [profile])

  if (profile) return <>{children}</>

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      const user = await createUser(newUsername)
      setProfile({ username: user.username, displayName: user.display_name })
    } catch (err) {
      setStatus((err as Error).message)
    }
  }

  return (
    <div className="relative z-20 flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm rounded-xl border border-stone-200/70 bg-white/90 p-6 shadow-lg backdrop-blur-md dark:border-slate-800/70 dark:bg-slate-900/80">
        <h2 className="mb-1 text-lg font-semibold text-stone-900 dark:text-slate-100">Who's working today?</h2>
        <p className="mb-4 text-sm text-stone-600 dark:text-slate-400">
          Pick an existing profile or create a new one — no password needed.
        </p>
        {users.length > 0 && (
          <ul className="mb-4 space-y-1">
            {users.map((u) => (
              <li key={u.id}>
                <button
                  onClick={() => setProfile({ username: u.username, displayName: u.display_name })}
                  className="w-full rounded-md border border-stone-200 px-3 py-2 text-left text-sm hover:bg-stone-100 dark:border-slate-700 dark:hover:bg-slate-800"
                >
                  {u.display_name}
                </button>
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={handleCreate} className="flex gap-2">
          <input
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
            placeholder="new username"
            required
            className={INPUT}
          />
          <button
            type="submit"
            className="rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-cyan-500 dark:text-slate-950"
          >
            Create
          </button>
        </form>
        {status && <p className="mt-2 text-sm text-rose-600 dark:text-rose-400">{status}</p>}
      </div>
    </div>
  )
}

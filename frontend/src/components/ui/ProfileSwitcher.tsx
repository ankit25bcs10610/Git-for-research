import { useProfile } from '../../profile/ProfileContext'

export default function ProfileSwitcher() {
  const { profile, clearProfile } = useProfile()
  if (!profile) return null

  return (
    <button
      onClick={clearProfile}
      title="Switch profile"
      className="rounded-full border border-stone-300 px-3 py-1.5 text-xs font-medium text-stone-600 transition-colors hover:bg-stone-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
    >
      {profile.displayName}
    </button>
  )
}

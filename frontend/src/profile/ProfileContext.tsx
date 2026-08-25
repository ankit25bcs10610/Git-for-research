import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export interface Profile {
  username: string
  displayName: string
}

const STORAGE_KEY = 'gfr-profile'

const ProfileContext = createContext<{
  profile: Profile | null
  setProfile: (profile: Profile) => void
  clearProfile: () => void
} | null>(null)

function readInitialProfile(): Profile | null {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (!stored) return null
  try {
    return JSON.parse(stored) as Profile
  } catch {
    return null
  }
}

export function ProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfileState] = useState<Profile | null>(readInitialProfile)

  useEffect(() => {
    if (profile) localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
    else localStorage.removeItem(STORAGE_KEY)
  }, [profile])

  return (
    <ProfileContext.Provider
      value={{ profile, setProfile: setProfileState, clearProfile: () => setProfileState(null) }}
    >
      {children}
    </ProfileContext.Provider>
  )
}

export function useProfile() {
  const ctx = useContext(ProfileContext)
  if (!ctx) throw new Error('useProfile must be used within a ProfileProvider')
  return ctx
}

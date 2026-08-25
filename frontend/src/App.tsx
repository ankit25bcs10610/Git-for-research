import { useState } from 'react'
import WaveBackground from './components/WaveBackground'
import LandingPage from './components/LandingPage'
import WorkspaceApp from './components/WorkspaceApp'
import ProfileGate from './components/ProfileGate'
import ThemeToggle from './components/ui/ThemeToggle'
import ProfileSwitcher from './components/ui/ProfileSwitcher'

function App() {
  const [entered, setEntered] = useState(false)

  return (
    <div className="relative min-h-screen p-4 md:p-8">
      <WaveBackground />
      <div className="fixed right-4 top-4 z-10 flex items-center gap-2 md:right-8 md:top-8">
        <ProfileSwitcher />
        <ThemeToggle />
      </div>
      <ProfileGate>
        {entered ? (
          <WorkspaceApp onBack={() => setEntered(false)} />
        ) : (
          <LandingPage onStart={() => setEntered(true)} />
        )}
      </ProfileGate>
    </div>
  )
}

export default App

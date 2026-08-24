import { WorkspaceView } from './components/WorkspaceView'
import { SearchChatPanel } from './components/SearchChatPanel'

function App() {
  return (
    <div>
      <h1>Git for Research</h1>
      <WorkspaceView workspaceId="demo-workspace" />
      <SearchChatPanel />
    </div>
  )
}

export default App

import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import App from './App'
import * as client from './api/client'

describe('App', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    // App now renders WorkspaceView, which fetches artifacts on mount via a
    // useEffect. Mock it here so this test stays focused on the heading and
    // doesn't make a real (unmocked) fetch call or warn about act().
    vi.spyOn(client, 'fetchArtifacts').mockResolvedValue([])
  })

  it('renders the heading text', async () => {
    render(<App />)
    expect(screen.getByText('Git for Research')).toBeInTheDocument()

    // Wait for WorkspaceView's mounting useEffect (which calls
    // fetchArtifacts) to settle so React doesn't warn about a state update
    // happening after the test has already finished.
    await waitFor(() => {
      expect(client.fetchArtifacts).toHaveBeenCalledWith('demo-workspace')
    })
  })
})

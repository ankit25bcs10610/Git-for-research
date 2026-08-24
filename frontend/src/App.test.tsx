import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders the heading text', () => {
    render(<App />)
    expect(screen.getByText('Git for Research')).toBeInTheDocument()
  })
})

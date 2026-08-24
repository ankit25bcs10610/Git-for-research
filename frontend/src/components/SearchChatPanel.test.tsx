import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SearchChatPanel } from './SearchChatPanel';
import * as client from '../api/client';

describe('SearchChatPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders mocked results with visible provenance labels after a submitted query', async () => {
    vi.spyOn(client, 'searchQuery').mockResolvedValue([
      {
        chunkId: 'chunk-1',
        text: 'the mitochondria is the powerhouse of the cell',
        artifactId: 'artifact-1',
        commitRef: 'commit-abc',
        score: 0.87,
      },
      {
        chunkId: 'chunk-2',
        text: 'ribosomes synthesize proteins from amino acids',
        artifactId: 'artifact-2',
        commitRef: 'commit-def',
        score: 0.65,
      },
    ]);

    render(<SearchChatPanel />);

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'cell biology' } });

    const button = screen.getByRole('button', { name: /search/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/the mitochondria is the powerhouse of the cell/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/ribosomes synthesize proteins from amino acids/i)).toBeInTheDocument();
    expect(screen.getByText('artifact-1 @ commit-abc')).toBeInTheDocument();
    expect(screen.getByText('artifact-2 @ commit-def')).toBeInTheDocument();
    expect(client.searchQuery).toHaveBeenCalledWith('cell biology');
  });
});

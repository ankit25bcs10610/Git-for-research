import React, { useState } from 'react';
import { searchQuery, SearchResult } from '../api/client';

export function SearchChatPanel() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const found = await searchQuery(query);
      setResults(found);
    } catch (err) {
      setError('search failed, please try again');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="search-chat-panel">
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="ask a question about your research"
        />
        <button type="submit" disabled={isLoading}>
          Search
        </button>
      </form>
      {error && <div className="search-error">{error}</div>}
      <ul className="search-results">
        {results.map((r) => (
          <li key={r.chunkId} className="search-result-item">
            <div className="search-result-text">{r.text}</div>
            <div className="search-result-provenance">
              {r.artifactId} @ {r.commitRef}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

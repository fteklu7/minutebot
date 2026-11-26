import { useState } from "react";
import { Link } from "react-router-dom";
import { api, formatDate } from "../api";

export default function Search() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    if (!query.trim()) return;
    setBusy(true);
    setError("");
    try {
      setResults(await api.search(query));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h2>Search past meetings</h2>
      <form className="row" onSubmit={submit}>
        <input
          placeholder='e.g. "what did we decide about the food budget?"'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          maxLength={500}
        />
        <button type="submit" disabled={busy}>{busy ? "Searching..." : "Search"}</button>
      </form>

      {error && <p className="error">{error}</p>}
      {results?.length === 0 && <p className="muted">No matches.</p>}
      <ul className="results">
        {results?.map((r, i) => (
          <li key={i} className="card">
            <Link to={`/meetings/${r.meeting_id}`}>{r.meeting_title}</Link>
            <span className="muted"> · {formatDate(r.meeting_date)}</span>
            <p>{r.text}</p>
          </li>
        ))}
      </ul>
    </>
  );
}

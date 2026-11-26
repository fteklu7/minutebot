import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, formatDate } from "../api";

function UploadForm({ onUploaded }) {
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileInput = useRef(null);

  async function submit(e) {
    e.preventDefault();
    if (!file) return setError("Pick a file first.");
    setBusy(true);
    setError("");

    const form = new FormData();
    form.append("title", title);
    if (date) form.append("meeting_date", date);
    form.append("file", file);

    try {
      const meeting = await api.uploadMeeting(form);
      setTitle("");
      setDate("");
      setFile(null);
      fileInput.current.value = "";
      onUploaded(meeting);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card upload" onSubmit={submit}>
      <h2>New meeting</h2>
      <div className="row">
        <input
          placeholder="Title, e.g. GBM week 9"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={200}
          required
        />
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </div>
      <input
        ref={fileInput}
        type="file"
        accept=".mp3,.m4a,.wav,.webm,.mp4,.mpeg,.mpga,.ogg,.txt"
        onChange={(e) => setFile(e.target.files[0] || null)}
      />
      <p className="muted small">Audio recording (up to 25 MB) or a .txt transcript.</p>
      <button type="submit" disabled={busy}>{busy ? "Uploading..." : "Upload"}</button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}

export default function Meetings() {
  const [meetings, setMeetings] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.meetings().then(setMeetings).catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <UploadForm onUploaded={(m) => navigate(`/meetings/${m.id}`)} />

      <h2>Past meetings</h2>
      {error && <p className="error">{error}</p>}
      {meetings === null && !error && <p className="muted">Loading...</p>}
      {meetings?.length === 0 && <p className="muted">No meetings yet. Upload one above.</p>}
      <ul className="list">
        {meetings?.map((m) => (
          <li key={m.id}>
            <Link to={`/meetings/${m.id}`}>{m.title}</Link>
            <span className="muted">{formatDate(m.meeting_date)}</span>
            {m.status !== "done" && <span className={`badge ${m.status}`}>{m.status}</span>}
            {m.open_items > 0 && <span className="badge">{m.open_items} open</span>}
          </li>
        ))}
      </ul>
    </>
  );
}

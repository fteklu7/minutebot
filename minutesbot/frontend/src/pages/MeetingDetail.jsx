import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, formatDate } from "../api";
import ItemRow from "../ItemRow";

export default function MeetingDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [meeting, setMeeting] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let timer;

    async function load() {
      try {
        const m = await api.meeting(id);
        if (cancelled) return;
        setMeeting(m);
        // keep checking until the background job finishes
        if (m.status === "processing") timer = setTimeout(load, 3000);
      } catch (e) {
        if (!cancelled) setError(e.message);
      }
    }
    load();

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id]);

  async function remove() {
    if (!window.confirm("Delete this meeting and its action items?")) return;
    try {
      await api.deleteMeeting(id);
      navigate("/");
    } catch (e) {
      setError(e.message);
    }
  }

  function replaceItem(updated) {
    setMeeting((m) => ({
      ...m,
      action_items: m.action_items.map((i) => (i.id === updated.id ? updated : i)),
    }));
  }

  if (error) return <p className="error">{error}</p>;
  if (!meeting) return <p className="muted">Loading...</p>;

  return (
    <>
      <div className="title-row">
        <div>
          <h2>{meeting.title}</h2>
          <p className="muted">{formatDate(meeting.meeting_date)}</p>
        </div>
        <button className="secondary" onClick={remove}>Delete</button>
      </div>

      {meeting.status === "processing" && (
        <p className="card">Working on it... transcribing and pulling out action items. This page will update.</p>
      )}
      {meeting.status === "failed" && <p className="card error">Processing failed: {meeting.error}</p>}

      {meeting.status === "done" && (
        <>
          <section className="card">
            <h3>Summary</h3>
            <p>{meeting.summary || <span className="muted">No summary.</span>}</p>
          </section>

          <section className="card">
            <h3>Decisions</h3>
            {meeting.decisions.length === 0 ? (
              <p className="muted">None recorded.</p>
            ) : (
              <ul>{meeting.decisions.map((d, i) => <li key={i}>{d}</li>)}</ul>
            )}
          </section>

          <section className="card">
            <h3>Action items</h3>
            {meeting.action_items.length === 0 ? (
              <p className="muted">Nobody committed to anything.</p>
            ) : (
              <ul className="items">
                {meeting.action_items.map((item) => (
                  <ItemRow key={item.id} item={item} onChange={replaceItem} />
                ))}
              </ul>
            )}
          </section>
        </>
      )}

      {meeting.transcript && (
        <details className="card">
          <summary>Full transcript</summary>
          <p className="transcript">{meeting.transcript}</p>
        </details>
      )}
    </>
  );
}

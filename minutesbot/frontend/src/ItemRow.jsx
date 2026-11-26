import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatDate } from "./api";

function todayLocal() {
  // toISOString() is UTC, which is already "tomorrow" after 7pm in Indiana
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function isOverdue(item) {
  if (item.done || !item.due_date) return false;
  return item.due_date < todayLocal();
}

// one action item. Used on the meeting page and the action items page.
export default function ItemRow({ item, onChange, showMeeting = false }) {
  const [owner, setOwner] = useState(item.owner ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => setOwner(item.owner ?? ""), [item.owner]);

  async function update(changes) {
    setSaving(true);
    setError("");
    try {
      const updated = await api.updateItem(item.id, changes);
      onChange(updated);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  function saveOwner() {
    if (owner.trim() !== (item.owner ?? "")) update({ owner });
  }

  return (
    <li className={`item ${item.done ? "done" : ""}`}>
      <input
        type="checkbox"
        checked={item.done}
        disabled={saving}
        onChange={(e) => update({ done: e.target.checked })}
        aria-label="Mark done"
      />
      <div className="item-body">
        <span className="task">{item.task}</span>
        <div className="item-meta">
          <input
            className="owner"
            placeholder="Unassigned"
            value={owner}
            maxLength={100}
            disabled={saving}
            onChange={(e) => setOwner(e.target.value)}
            onBlur={saveOwner}
            onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
            aria-label="Owner"
          />
          <input
            type="date"
            value={item.due_date ?? ""}
            disabled={saving}
            onChange={(e) => update({ due_date: e.target.value || null })}
            aria-label="Due date"
          />
          {isOverdue(item) && <span className="badge overdue">overdue</span>}
          {item.due_date && !isOverdue(item) && !item.done && (
            <span className="muted">due {formatDate(item.due_date)}</span>
          )}
          {showMeeting && <Link to={`/meetings/${item.meeting_id}`}>from meeting</Link>}
        </div>
        {error && <p className="error">{error}</p>}
      </div>
    </li>
  );
}

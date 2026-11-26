import { useEffect, useState } from "react";
import { api } from "../api";
import ItemRow from "../ItemRow";

export default function ActionItems() {
  const [items, setItems] = useState(null);
  const [ownerFilter, setOwnerFilter] = useState("");
  const [showDone, setShowDone] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setItems(null);
    api
      .actionItems({ open_only: !showDone })
      .then(setItems)
      .catch((e) => setError(e.message));
  }, [showDone]);

  function replaceItem(updated) {
    setItems((list) =>
      list
        .map((i) => (i.id === updated.id ? updated : i))
        // if we're only showing open items, drop it once it's checked off
        .filter((i) => showDone || !i.done)
    );
  }

  const owners = [...new Set((items || []).map((i) => i.owner).filter(Boolean))].sort();
  const visible = (items || []).filter((i) => !ownerFilter || i.owner === ownerFilter);

  return (
    <>
      <h2>Action items</h2>

      <div className="row filters">
        <select value={ownerFilter} onChange={(e) => setOwnerFilter(e.target.value)}>
          <option value="">Everyone</option>
          {owners.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
        <label>
          <input type="checkbox" checked={showDone} onChange={(e) => setShowDone(e.target.checked)} />
          Show completed
        </label>
      </div>

      {error && <p className="error">{error}</p>}
      {items === null && !error && <p className="muted">Loading...</p>}
      {items && visible.length === 0 && <p className="muted">Nothing here. Nice.</p>}
      <ul className="items">
        {visible.map((item) => (
          <ItemRow key={item.id} item={item} onChange={replaceItem} showMeeting />
        ))}
      </ul>
    </>
  );
}

import { useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { getKey, setKey } from "./api";
import Meetings from "./pages/Meetings";
import MeetingDetail from "./pages/MeetingDetail";
import ActionItems from "./pages/ActionItems";
import Search from "./pages/Search";

function AccessKey() {
  const [value, setValue] = useState(getKey());
  const [saved, setSaved] = useState(false);

  function save(e) {
    e.preventDefault();
    setKey(value.trim());
    setSaved(true);
    setTimeout(() => window.location.reload(), 300);
  }

  return (
    <form className="key-form" onSubmit={save}>
      <input
        type="password"
        placeholder="Access key"
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button type="submit">{saved ? "Saved" : "Save"}</button>
    </form>
  );
}

export default function App() {
  return (
    <div className="app">
      <header>
        <h1>MinutesBot</h1>
        <nav>
          <NavLink to="/" end>Meetings</NavLink>
          <NavLink to="/action-items">Action items</NavLink>
          <NavLink to="/search">Search</NavLink>
        </nav>
        <AccessKey />
      </header>

      <main>
        <Routes>
          <Route path="/" element={<Meetings />} />
          <Route path="/meetings/:id" element={<MeetingDetail />} />
          <Route path="/action-items" element={<ActionItems />} />
          <Route path="/search" element={<Search />} />
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </main>
    </div>
  );
}

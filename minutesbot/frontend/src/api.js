const KEY_STORAGE = "minutesbot_key";

export function getKey() {
  try {
    return localStorage.getItem(KEY_STORAGE) || "";
  } catch {
    return "";
  }
}

export function setKey(key) {
  try {
    localStorage.setItem(KEY_STORAGE, key);
  } catch {
    // private browsing etc, key just won't persist
  }
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const key = getKey();
  if (key) headers["X-Access-Key"] = key;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.json);
  }

  const res = await fetch(`/api${path}`, { ...options, headers });
  if (res.status === 204) return null;

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    let msg = data?.detail || `Request failed (${res.status})`;
    // pydantic validation errors come back as a list
    if (Array.isArray(msg)) msg = msg.map((d) => d.msg).join(", ");
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return data;
}

export const api = {
  meetings: () => request("/meetings"),
  meeting: (id) => request(`/meetings/${id}`),
  uploadMeeting: (formData) => request("/meetings", { method: "POST", body: formData }),
  deleteMeeting: (id) => request(`/meetings/${id}`, { method: "DELETE" }),

  actionItems: (params = {}) => request(`/action-items?${new URLSearchParams(params)}`),
  updateItem: (id, changes) => request(`/action-items/${id}`, { method: "PATCH", json: changes }),

  search: (q) => request(`/search?${new URLSearchParams({ q })}`),
};

export function formatDate(iso) {
  if (!iso) return "";
  // dates come back as YYYY-MM-DD. new Date() would read that as UTC
  // and show the day before for anyone in the US, so split it manually
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

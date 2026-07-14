-- feature-usage + problem events (functions/api/evento.js; sent via sendBeacon from the map)
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (datetime('now')),
  event TEXT NOT NULL,   -- e.g. plan_search, route_select, js_error
  label TEXT,            -- small context: option count, route id, error msg (truncated)
  path TEXT,
  visitor TEXT,
  ip TEXT,
  ua TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts);
CREATE INDEX IF NOT EXISTS idx_events_event ON events (event);

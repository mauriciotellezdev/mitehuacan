-- per-route service window + headway, edited in /system/horarios
-- (functions/api/horarios.js). route_id = properties.id in the routes dataset.
CREATE TABLE IF NOT EXISTS route_schedules (
  route_id TEXT PRIMARY KEY,
  first_run TEXT,                 -- 'HH:MM' local, first departure
  last_run TEXT,                  -- 'HH:MM' local, last departure
  headway_min INTEGER,            -- typical minutes between combis
  notes TEXT,                     -- free text, e.g. 'domingos cada 20 min'
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

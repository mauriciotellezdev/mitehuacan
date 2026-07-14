-- named route drafts produced by the /system/map editor (trim/simplify/align of
-- raw positions). Pulled into the repo dataset by tehuacan/scripts/14_import_drafts.py
CREATE TABLE IF NOT EXISTS route_drafts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,          -- route name as painted on the combi
  device TEXT,
  t0 TEXT, t1 TEXT,            -- source time window
  n_source INTEGER,            -- raw points loaded
  geometry TEXT NOT NULL,      -- GeoJSON LineString coordinates [[lon,lat],...]
  status TEXT NOT NULL DEFAULT 'draft'  -- draft | imported
);

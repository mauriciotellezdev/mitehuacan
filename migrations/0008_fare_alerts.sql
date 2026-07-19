-- fare per line (shown in the route sheet) + service alerts (Alertas tab)
ALTER TABLE combi_lines ADD COLUMN fare_mxn REAL;
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  line_slug TEXT,                 -- NULL = system-wide notice
  message TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts (active);

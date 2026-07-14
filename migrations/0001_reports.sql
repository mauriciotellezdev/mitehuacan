-- D1 schema for citizen route reports (functions/api/reportes.js)
-- apply: wrangler d1 migrations apply quecombi --remote
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  ciudad TEXT NOT NULL DEFAULT 'tehuacan',
  nombre TEXT NOT NULL,          -- route name as painted on the van
  descripcion TEXT NOT NULL,     -- where it runs, in the reporter's words
  ip_hash TEXT NOT NULL,         -- sha256 of reporter IP, rate limiting only
  status TEXT NOT NULL DEFAULT 'new'  -- new | reviewing | mapped | rejected
);
CREATE INDEX IF NOT EXISTS idx_reports_ip_day ON reports (ip_hash, created_at);

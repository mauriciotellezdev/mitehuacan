-- first-party analytics: server-side page hits (functions/_middleware.js)
-- IPs are personal data: readable only via token-protected /system + /api/stats; 90-day retention purge.
CREATE TABLE IF NOT EXISTS hits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (datetime('now')),
  path TEXT NOT NULL,
  query TEXT,
  qr TEXT,              -- sticker id when the visit came from a /qr/ scan
  visitor TEXT,         -- first-party cookie id (qcv); cookie+ip mix identifies revisits
  is_new INTEGER NOT NULL DEFAULT 0,  -- 1 when the visitor cookie was issued on this hit
  ip TEXT NOT NULL,
  country TEXT,
  region TEXT,
  city TEXT,
  asn TEXT,
  ua TEXT,              -- user agent (browser/device)
  referer TEXT,
  lang TEXT
);
CREATE INDEX IF NOT EXISTS idx_hits_ts ON hits (ts);
CREATE INDEX IF NOT EXISTS idx_hits_qr ON hits (qr) WHERE qr IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_hits_visitor ON hits (visitor);
CREATE INDEX IF NOT EXISTS idx_hits_ip ON hits (ip);

-- GPS positions from Traccar Client (osmand protocol) via functions/api/gps.js
-- publicly hosted ingest: the phone posts here over mobile data; no laptop involved.
CREATE TABLE IF NOT EXISTS positions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device TEXT NOT NULL,          -- device identifier (allowlisted via GPS_DEVICES env)
  fix_ts TEXT NOT NULL,          -- GPS fix time (client-supplied; trips key on this)
  received_at TEXT NOT NULL DEFAULT (datetime('now')),
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  speed REAL,                    -- knots, as sent by traccar client
  bearing REAL,
  altitude REAL,
  accuracy REAL,
  batt REAL
);
CREATE INDEX IF NOT EXISTS idx_positions_device_ts ON positions (device, fix_ts);

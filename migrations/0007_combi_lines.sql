-- combi lines: the operating line is the first-class admin entity
-- (/system/combis). A line owns its schedule; recorded GPS drafts
-- (route_drafts) attach to a line via line_slug (NULL = unattached inbox).
-- Replaces route_schedules (created same week, never populated in prod).
CREATE TABLE IF NOT EXISTS combi_lines (
  slug TEXT PRIMARY KEY,          -- matches routes.js properties.id once published
  name TEXT NOT NULL,
  first_run TEXT,                 -- 'HH:MM' first departure
  last_run TEXT,                  -- 'HH:MM' last departure
  headway_min INTEGER,            -- minutes between combis
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
ALTER TABLE route_drafts ADD COLUMN line_slug TEXT;
DROP TABLE IF EXISTS route_schedules;

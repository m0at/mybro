-- mybro initial schema
-- PostgreSQL database for project management + ticketing

CREATE TABLE IF NOT EXISTS projects (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    repo_path   VARCHAR(500),
    github_url  VARCHAR(500),
    description TEXT,
    status      VARCHAR(20) DEFAULT 'active',
    color       VARCHAR(7) DEFAULT '#3b82f6',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tickets (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER REFERENCES projects(id),
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    status          VARCHAR(20) DEFAULT 'backlog',
    priority        VARCHAR(10) DEFAULT 'medium',
    labels          TEXT[] DEFAULT '{}',
    assignee        VARCHAR(50) DEFAULT 'andy',
    due_date        DATE,
    estimated_hours REAL,
    actual_hours    REAL,
    parent_id       INTEGER REFERENCES tickets(id),
    sort_order      INTEGER DEFAULT 0,
    created_by      VARCHAR(50) DEFAULT 'user',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ticket_events (
    id          SERIAL PRIMARY KEY,
    ticket_id   INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    event_type  VARCHAR(30) NOT NULL,
    content     TEXT,
    author      VARCHAR(50) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS status_updates (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER REFERENCES projects(id),
    ticket_id   INTEGER REFERENCES tickets(id),
    content     TEXT NOT NULL,
    author      VARCHAR(50) NOT NULL,
    update_type VARCHAR(20) DEFAULT 'progress',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tpm_reports (
    id              SERIAL PRIMARY KEY,
    report          JSONB NOT NULL,
    issues_found    INTEGER DEFAULT 0,
    issues_fixed    INTEGER DEFAULT 0,
    reminders       JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS loc_snapshots (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER REFERENCES projects(id),
    date            DATE NOT NULL,
    lines_added     INTEGER DEFAULT 0,
    lines_removed   INTEGER DEFAULT 0,
    total_lines     INTEGER DEFAULT 0,
    commit_count    INTEGER DEFAULT 0,
    UNIQUE(project_id, date)
);

CREATE TABLE IF NOT EXISTS droplets (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER REFERENCES projects(id),
    droplet_id      BIGINT UNIQUE,
    name            VARCHAR(200),
    ip_address      VARCHAR(45),
    status          VARCHAR(20),
    size_slug       VARCHAR(50),
    region          VARCHAR(10),
    monthly_cost    REAL,
    last_checked_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tickets_project ON tickets(project_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_ticket_events_ticket ON ticket_events(ticket_id);
CREATE INDEX IF NOT EXISTS idx_loc_snapshots_project_date ON loc_snapshots(project_id, date);
CREATE INDEX IF NOT EXISTS idx_status_updates_created ON status_updates(created_at DESC);

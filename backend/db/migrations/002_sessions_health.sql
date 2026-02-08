-- Sessions, snapshots, audits, health scoring

CREATE TABLE IF NOT EXISTS claude_sessions (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER REFERENCES projects(id),
    session_id      VARCHAR(100) NOT NULL UNIQUE,
    first_prompt    TEXT,
    summary         TEXT,
    message_count   INTEGER DEFAULT 0,
    input_tokens    BIGINT DEFAULT 0,
    output_tokens   BIGINT DEFAULT 0,
    cache_read_tokens BIGINT DEFAULT 0,
    model           VARCHAR(100),
    git_branch      VARCHAR(200),
    started_at      TIMESTAMPTZ,
    ended_at        TIMESTAMPTZ,
    duration_s      INTEGER DEFAULT 0,
    file_size_bytes BIGINT DEFAULT 0,
    ingested_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_snapshots (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER REFERENCES projects(id),
    snapshot_type   VARCHAR(30) NOT NULL,  -- 'git', 'loc', 'process'
    data            JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repo_audits (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER REFERENCES projects(id) UNIQUE,
    readme_excerpt  TEXT,
    claude_md       TEXT,
    todo_md         TEXT,
    key_files       JSONB,            -- {filename: first_line_or_description}
    last_scanned_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_health (
    id                  SERIAL PRIMARY KEY,
    project_id          INTEGER REFERENCES projects(id) UNIQUE,
    score               INTEGER DEFAULT 0,      -- 0-100
    label               VARCHAR(20) DEFAULT 'unknown',  -- hot, active, stale, dead
    commit_velocity_7d  INTEGER DEFAULT 0,
    session_count_7d    INTEGER DEFAULT 0,
    last_session_at     TIMESTAMPTZ,
    last_commit_at      TIMESTAMPTZ,
    open_tickets        INTEGER DEFAULT 0,
    has_server          BOOLEAN DEFAULT FALSE,
    has_claude          BOOLEAN DEFAULT FALSE,
    details             JSONB,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_claude_sessions_project ON claude_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_claude_sessions_started ON claude_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_project_snapshots_project_type ON project_snapshots(project_id, snapshot_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_project_health_score ON project_health(score DESC);

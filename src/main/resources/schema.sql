CREATE TABLE IF NOT EXISTS trajectory_points (
    id              BIGSERIAL PRIMARY KEY,
    session_id      VARCHAR(64)  NOT NULL,
    x               DOUBLE       NOT NULL,
    y               DOUBLE       NOT NULL,
    z               DOUBLE       NOT NULL,
    timestamp       TIMESTAMPTZ  NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trajectory_points_session_id ON trajectory_points(session_id);
CREATE INDEX IF NOT EXISTS idx_trajectory_points_timestamp ON trajectory_points(timestamp);

CREATE TABLE IF NOT EXISTS audit_results (
    id                    BIGSERIAL PRIMARY KEY,
    session_id            VARCHAR(64)  NOT NULL,
    has_collision_risk    BOOLEAN      NOT NULL,
    has_jitter_anomaly    BOOLEAN      NOT NULL,
    collision_risk_score  DOUBLE,
    jitter_score          DOUBLE,
    details               VARCHAR(2000),
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_results_session_id ON audit_results(session_id);

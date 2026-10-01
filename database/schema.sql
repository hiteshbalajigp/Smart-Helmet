-- PostgreSQL schema for Smart Helmet Violation Detection System

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS violations (
    id SERIAL PRIMARY KEY,
    violation_id VARCHAR(64) NOT NULL UNIQUE,
    violation_type VARCHAR(32) NOT NULL,
    plate_text VARCHAR(32),
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    device_id VARCHAR(64) NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    timestamp TIMESTAMPTZ NOT NULL,
    snapshot_path TEXT,
    video_path TEXT,
    metadata_json TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_violations_violation_id ON violations (violation_id);
CREATE INDEX IF NOT EXISTS ix_violations_violation_type ON violations (violation_type);
CREATE INDEX IF NOT EXISTS ix_violations_plate_text ON violations (plate_text);
CREATE INDEX IF NOT EXISTS ix_violations_device_id ON violations (device_id);
CREATE INDEX IF NOT EXISTS ix_violations_timestamp ON violations (timestamp);
CREATE INDEX IF NOT EXISTS ix_violations_plate_timestamp ON violations (plate_text, timestamp);

COMMENT ON TABLE violations IS 'Traffic violation records from edge helmet devices';

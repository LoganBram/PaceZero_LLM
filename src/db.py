import sqlite3
import json
from datetime import datetime

DB_PATH = "db/lp_engine.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS organizations (
            org_name        TEXT PRIMARY KEY,
            org_type        TEXT,
            region          TEXT,
            aum_estimated   TEXT,
            is_lp_eligible  INTEGER,
            enrichment_summary TEXT,
            enrichment_raw  TEXT,
            enriched_at     TEXT
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_name    TEXT,
            org_name        TEXT REFERENCES organizations(org_name),
            role            TEXT,
            email           TEXT,
            region          TEXT,
            contact_status  TEXT,
            relationship_depth INTEGER
        );

        CREATE TABLE IF NOT EXISTS scores (
            org_name            TEXT PRIMARY KEY REFERENCES organizations(org_name),
            sector_fit_score    REAL,
            sector_fit_confidence TEXT,
            sector_fit_reasoning TEXT,
            halo_score          REAL,
            halo_confidence     TEXT,
            halo_reasoning      TEXT,
            emerging_fit_score  REAL,
            emerging_fit_confidence TEXT,
            emerging_fit_reasoning TEXT,
            composite_score     REAL,
            tier                TEXT,
            check_size_range    TEXT,
            flags               TEXT,
            scored_at           TEXT
        );

        CREATE TABLE IF NOT EXISTS enrichment_runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at      TEXT,
            completed_at    TEXT,
            orgs_processed  INTEGER DEFAULT 0,
            orgs_skipped    INTEGER DEFAULT 0,
            total_input_tokens  INTEGER DEFAULT 0,
            total_output_tokens INTEGER DEFAULT 0,
            estimated_cost_usd  REAL DEFAULT 0.0,
            status          TEXT DEFAULT 'running'
        );
    """)

    conn.commit()
    conn.close()
    print("DB initialized.")

def is_org_enriched(conn, org_name):
    row = conn.execute(
        "SELECT org_name FROM organizations WHERE org_name = ? AND enriched_at IS NOT NULL",
        (org_name,)
    ).fetchone()
    return row is not None

def save_enrichment(conn, contact, result, usage):
    now = datetime.utcnow().isoformat()

    # upsert organization
    conn.execute("""
        INSERT INTO organizations (org_name, org_type, region, aum_estimated, is_lp_eligible, enrichment_summary, enrichment_raw, enriched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(org_name) DO UPDATE SET
            aum_estimated = excluded.aum_estimated,
            is_lp_eligible = excluded.is_lp_eligible,
            enrichment_summary = excluded.enrichment_summary,
            enrichment_raw = excluded.enrichment_raw,
            enriched_at = excluded.enriched_at
    """, (
        result["org"],
        contact["Org Type"],
        contact["Region"],
        result.get("aum_estimated"),
        1 if result.get("is_lp_eligible") else 0,
        result.get("enrichment_summary"),
        json.dumps(result),
        now,
    ))

    # upsert contact
    conn.execute("""
        INSERT INTO contacts (contact_name, org_name, role, email, region, contact_status, relationship_depth)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        contact["Contact Name"],
        result["org"],
        contact["Role"],
        contact.get("Email", ""),
        contact["Region"],
        contact["Contact Status"],
        int(contact["Relationship Depth"]),
    ))

    # upsert scores
    conn.execute("""
        INSERT INTO scores (org_name, sector_fit_score, sector_fit_confidence, sector_fit_reasoning,
            halo_score, halo_confidence, halo_reasoning,
            emerging_fit_score, emerging_fit_confidence, emerging_fit_reasoning,
            check_size_range, flags, scored_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(org_name) DO UPDATE SET
            sector_fit_score = excluded.sector_fit_score,
            sector_fit_confidence = excluded.sector_fit_confidence,
            sector_fit_reasoning = excluded.sector_fit_reasoning,
            halo_score = excluded.halo_score,
            halo_confidence = excluded.halo_confidence,
            halo_reasoning = excluded.halo_reasoning,
            emerging_fit_score = excluded.emerging_fit_score,
            emerging_fit_confidence = excluded.emerging_fit_confidence,
            emerging_fit_reasoning = excluded.emerging_fit_reasoning,
            check_size_range = excluded.check_size_range,
            flags = excluded.flags,
            scored_at = excluded.scored_at
    """, (
        result["org"],
        result["sector_fit"]["score"],
        result["sector_fit"]["confidence"],
        result["sector_fit"]["reasoning"],
        result["halo_value"]["score"],
        result["halo_value"]["confidence"],
        result["halo_value"]["reasoning"],
        result["emerging_fit"]["score"],
        result["emerging_fit"]["confidence"],
        result["emerging_fit"]["reasoning"],
        result.get("check_size_range"),
        json.dumps(result.get("flags", [])),
        now,
    ))

    conn.commit()

def get_all_results(conn):
    return conn.execute("""
        SELECT
            o.org_name, o.org_type, o.region, o.aum_estimated, o.is_lp_eligible, o.enrichment_summary,
            s.sector_fit_score, s.sector_fit_confidence, s.sector_fit_reasoning,
            s.halo_score, s.halo_confidence, s.halo_reasoning,
            s.emerging_fit_score, s.emerging_fit_confidence, s.emerging_fit_reasoning,
            s.composite_score, s.tier, s.check_size_range, s.flags,
            c.contact_name, c.role, c.contact_status, c.relationship_depth
        FROM organizations o
        JOIN scores s ON o.org_name = s.org_name
        JOIN contacts c ON o.org_name = c.org_name
        ORDER BY s.composite_score DESC
    """).fetchall()

if __name__ == "__main__":
    init_db()
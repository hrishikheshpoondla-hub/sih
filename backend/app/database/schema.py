"""
backend/app/database/schema.py
Complete DuckDB SQL DDL schema for SIH26146.
Contains 14 normalized analytical tables, indexes, and initialization scripts.
"""

SCHEMA_DDL = """
-- Sequence generators for auto-incrementing identifiers
CREATE SEQUENCE IF NOT EXISTS seq_raw_records START 1;
CREATE SEQUENCE IF NOT EXISTS seq_transactions START 1;
CREATE SEQUENCE IF NOT EXISTS seq_inputs START 1;
CREATE SEQUENCE IF NOT EXISTS seq_outputs START 1;
CREATE SEQUENCE IF NOT EXISTS seq_wallets START 1;
CREATE SEQUENCE IF NOT EXISTS seq_network_obs START 1;
CREATE SEQUENCE IF NOT EXISTS seq_ips START 1;
CREATE SEQUENCE IF NOT EXISTS seq_entities START 1;
CREATE SEQUENCE IF NOT EXISTS seq_relationships START 1;
CREATE SEQUENCE IF NOT EXISTS seq_features START 1;
CREATE SEQUENCE IF NOT EXISTS seq_scores START 1;
CREATE SEQUENCE IF NOT EXISTS seq_evidence START 1;
CREATE SEQUENCE IF NOT EXISTS seq_alerts START 1;

-- 1. Ingestion Batches
CREATE TABLE IF NOT EXISTS ingestion_batches (
    batch_id VARCHAR PRIMARY KEY,
    filename VARCHAR NOT NULL,
    file_format VARCHAR NOT NULL,
    total_records INTEGER DEFAULT 0,
    valid_records INTEGER DEFAULT 0,
    invalid_records INTEGER DEFAULT 0,
    status VARCHAR DEFAULT 'PENDING',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 2. Raw Records (Preserves original data verbatim)
CREATE TABLE IF NOT EXISTS raw_records (
    raw_id BIGINT PRIMARY KEY DEFAULT nextval('seq_raw_records'),
    source_file VARCHAR NOT NULL,
    source_format VARCHAR NOT NULL,
    source_record_number INTEGER,
    raw_payload VARCHAR NOT NULL,
    ingestion_batch_id VARCHAR,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validation_status VARCHAR NOT NULL,
    validation_error VARCHAR
);

-- 3. Transactions (Blockchain Layer)
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id BIGINT PRIMARY KEY DEFAULT nextval('seq_transactions'),
    txid VARCHAR UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    fee DOUBLE DEFAULT 0.0,
    total_input_amount DOUBLE DEFAULT 0.0,
    total_output_amount DOUBLE DEFAULT 0.0,
    script_type VARCHAR DEFAULT 'p2pkh',
    source_record_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Transaction Inputs
CREATE TABLE IF NOT EXISTS transaction_inputs (
    input_id BIGINT PRIMARY KEY DEFAULT nextval('seq_inputs'),
    txid VARCHAR NOT NULL,
    wallet_address VARCHAR NOT NULL,
    amount DOUBLE NOT NULL,
    input_index INTEGER DEFAULT 0
);

-- 5. Transaction Outputs
CREATE TABLE IF NOT EXISTS transaction_outputs (
    output_id BIGINT PRIMARY KEY DEFAULT nextval('seq_outputs'),
    txid VARCHAR NOT NULL,
    wallet_address VARCHAR NOT NULL,
    amount DOUBLE NOT NULL,
    output_index INTEGER DEFAULT 0
);

-- 6. Wallets (Aggregated Wallet Entity State)
CREATE TABLE IF NOT EXISTS wallets (
    wallet_id BIGINT PRIMARY KEY DEFAULT nextval('seq_wallets'),
    wallet_address VARCHAR UNIQUE NOT NULL,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    total_transactions INTEGER DEFAULT 0,
    total_inbound_amount DOUBLE DEFAULT 0.0,
    total_outbound_amount DOUBLE DEFAULT 0.0,
    unique_counterparties INTEGER DEFAULT 0,
    unique_ips INTEGER DEFAULT 0,
    unique_countries INTEGER DEFAULT 0,
    unique_asns INTEGER DEFAULT 0
);

-- 7. Network Observations (P2P Network Layer)
CREATE TABLE IF NOT EXISTS network_observations (
    observation_id BIGINT PRIMARY KEY DEFAULT nextval('seq_network_obs'),
    timestamp TIMESTAMP NOT NULL,
    src_ip VARCHAR NOT NULL,
    dst_ip VARCHAR NOT NULL,
    src_port INTEGER NOT NULL,
    dst_port INTEGER NOT NULL,
    txid VARCHAR NOT NULL,
    source_record_id BIGINT
);

-- 8. IP Addresses
CREATE TABLE IF NOT EXISTS ip_addresses (
    ip_id BIGINT PRIMARY KEY DEFAULT nextval('seq_ips'),
    ip_address VARCHAR UNIQUE NOT NULL,
    country VARCHAR,
    asn VARCHAR,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP
);

-- 9. Universal Entities (WALLET, IP, TXID)
CREATE TABLE IF NOT EXISTS entities (
    entity_id BIGINT PRIMARY KEY DEFAULT nextval('seq_entities'),
    entity_type VARCHAR NOT NULL, -- 'WALLET', 'IP', 'TXID'
    entity_value VARCHAR UNIQUE NOT NULL,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP
);

-- 10. Entity Relationships (Graph Topology Edges)
CREATE TABLE IF NOT EXISTS entity_relationships (
    relationship_id BIGINT PRIMARY KEY DEFAULT nextval('seq_relationships'),
    source_entity_id BIGINT NOT NULL,
    target_entity_id BIGINT NOT NULL,
    relationship_type VARCHAR NOT NULL, -- 'IP_TO_TXID', 'TXID_TO_WALLET', 'WALLET_TO_WALLET', 'IP_TO_WALLET'
    weight DOUBLE DEFAULT 1.0,
    transaction_count INTEGER DEFAULT 1,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP
);

-- 11. Entity Behavioral Features (Engineered for ML)
CREATE TABLE IF NOT EXISTS entity_features (
    feature_id BIGINT PRIMARY KEY DEFAULT nextval('seq_features'),
    entity_id BIGINT UNIQUE NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transaction_count INTEGER DEFAULT 0,
    transaction_frequency DOUBLE DEFAULT 0.0,
    transaction_volume DOUBLE DEFAULT 0.0,
    average_transaction_amount DOUBLE DEFAULT 0.0,
    transaction_amount_variance DOUBLE DEFAULT 0.0,
    unique_counterparties INTEGER DEFAULT 0,
    unique_ips INTEGER DEFAULT 0,
    unique_countries INTEGER DEFAULT 0,
    unique_asns INTEGER DEFAULT 0,
    inbound_volume DOUBLE DEFAULT 0.0,
    outbound_volume DOUBLE DEFAULT 0.0,
    inbound_outbound_ratio DOUBLE DEFAULT 0.0,
    fee_average DOUBLE DEFAULT 0.0,
    fee_variance DOUBLE DEFAULT 0.0,
    burst_frequency DOUBLE DEFAULT 0.0,
    graph_degree INTEGER DEFAULT 0,
    graph_weighted_degree DOUBLE DEFAULT 0.0,
    graph_centrality DOUBLE DEFAULT 0.0,
    cluster_size INTEGER DEFAULT 1
);

-- 12. Anomaly Scores (Isolation Forest & Statistical ML Output)
CREATE TABLE IF NOT EXISTS anomaly_scores (
    score_id BIGINT PRIMARY KEY DEFAULT nextval('seq_scores'),
    entity_id BIGINT NOT NULL,
    model_name VARCHAR NOT NULL,
    model_version VARCHAR NOT NULL,
    anomaly_score DOUBLE NOT NULL,
    normalized_risk_score DOUBLE NOT NULL, -- 0 to 100
    severity VARCHAR NOT NULL, -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13. Alert Evidence (Granular Transparent Feature Deviations)
CREATE TABLE IF NOT EXISTS alert_evidence (
    evidence_id BIGINT PRIMARY KEY DEFAULT nextval('seq_evidence'),
    alert_id VARCHAR NOT NULL,
    feature_name VARCHAR NOT NULL,
    feature_value DOUBLE NOT NULL,
    baseline_value DOUBLE NOT NULL,
    deviation_ratio DOUBLE NOT NULL,
    evidence_description VARCHAR NOT NULL
);

-- 14. Investigation Alerts (Investigator Review Queue)
CREATE TABLE IF NOT EXISTS investigation_alerts (
    alert_id VARCHAR PRIMARY KEY,
    entity_id BIGINT NOT NULL,
    anomaly_score_id BIGINT,
    severity VARCHAR NOT NULL,
    confidence DOUBLE NOT NULL,
    status VARCHAR DEFAULT 'NEW', -- 'NEW', 'INVESTIGATING', 'REVIEWED', 'DISMISSED'
    title VARCHAR NOT NULL,
    ai_explanation VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optimized Analytical Indexes
CREATE INDEX IF NOT EXISTS idx_transactions_txid ON transactions(txid);
CREATE INDEX IF NOT EXISTS idx_inputs_txid ON transaction_inputs(txid);
CREATE INDEX IF NOT EXISTS idx_inputs_wallet ON transaction_inputs(wallet_address);
CREATE INDEX IF NOT EXISTS idx_outputs_txid ON transaction_outputs(txid);
CREATE INDEX IF NOT EXISTS idx_outputs_wallet ON transaction_outputs(wallet_address);
CREATE INDEX IF NOT EXISTS idx_net_obs_txid ON network_observations(txid);
CREATE INDEX IF NOT EXISTS idx_net_obs_src_ip ON network_observations(src_ip);
CREATE INDEX IF NOT EXISTS idx_entities_val ON entities(entity_value);
CREATE INDEX IF NOT EXISTS idx_relationships_src ON entity_relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_tgt ON entity_relationships(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_alerts_entity ON investigation_alerts(entity_id);
CREATE INDEX IF NOT EXISTS idx_evidence_alert ON alert_evidence(alert_id);
"""

def init_schema(conn):
    """Initializes all 14 tables and indexes on the provided DuckDB connection."""
    conn.execute(SCHEMA_DDL)

def reset_schema(conn):
    """Drops existing tables and resets the schema cleanly."""
    tables = [
        "alert_evidence", "investigation_alerts", "anomaly_scores",
        "entity_features", "entity_relationships", "entities",
        "ip_addresses", "network_observations", "wallets",
        "transaction_outputs", "transaction_inputs", "transactions",
        "raw_records", "ingestion_batches"
    ]
    for table in tables:
        conn.execute(f"DROP TABLE IF EXISTS {table};")
    init_schema(conn)

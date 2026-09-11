# SIH26146 Database Architecture Documentation

## Storage Engine: DuckDB
DuckDB is an in-process columnar SQL database optimized for high-performance analytical queries (OLAP). It requires zero server setup, zero internet connectivity, and stores data in a single local portable file: `data/database/sih26146.duckdb`.

---

## Complete Table Catalog (14 Tables)

1. **`ingestion_batches`**: Tracks dataset ingestion batches, files, status, and validation statistics.
2. **`raw_records`**: Immutable raw ingestion payloads storing exact line/object text with validation status (`VALID`, `MALFORMED`, `INVALID_FIELD`).
3. **`transactions`**: First-class blockchain transaction records containing `txid`, `timestamp`, `fee`, `total_input_amount`, `total_output_amount`, and `script_type`.
4. **`transaction_inputs`**: Normalized individual transaction input legs (`txid`, `wallet_address`, `amount`, `input_index`).
5. **`transaction_outputs`**: Normalized individual transaction output legs (`txid`, `wallet_address`, `amount`, `output_index`).
6. **`wallets`**: Aggregated wallet entity ledger with transaction count, inbound/outbound volume, counterparties, and unique network associations.
7. **`network_observations`**: P2P network traffic layer metadata recording `src_ip`, `dst_ip`, `src_port`, `dst_port`, `timestamp`, and `txid`.
8. **`ip_addresses`**: Monitored IP addresses with geo-location (country) and Autonomous System Number (ASN).
9. **`entities`**: Unified entity registry for graph nodes (`WALLET`, `IP`, `TXID`).
10. **`entity_relationships`**: Graph edges representing correlated flows (`IP_TO_TXID`, `TXID_TO_WALLET`, `WALLET_TO_WALLET`, `IP_TO_WALLET`).
11. **`entity_features`**: Behavioral metrics computed per entity (transaction frequency, burstiness, variance, in/out ratio, graph degree, centrality).
12. **`anomaly_scores`**: Unsupervised Isolation Forest model predictions, normalized risk scores (0-100), and severity levels.
13. **`alert_evidence`**: Transparent forensic evidence items comparing entity feature values to baseline population statistics.
14. **`investigation_alerts`**: High-priority alert dossier queue for analysts with investigator status (`NEW`, `INVESTIGATING`, `REVIEWED`, `DISMISSED`) and local AI narratives.

---

## Maintenance & Initialization
- To initialize or reset the database:
  ```bash
  python scripts/init_database.py --reset
  ```

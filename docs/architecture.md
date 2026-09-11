# SIH26146 System Architecture

**Organization**: National Technical Research Organisation (NTRO)  
**Theme**: Blockchain & Cybersecurity  
**Challenge**: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

---

## 1. High-Level Architecture

```
                       +-----------------------------------+
                       | BULK DATA INGESTION ENGINE        |
                       | CSV, JSON, XML Multi-format Parse |
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------------------------+
                       | STRICT VALIDATION & DE-DUPLICATION|
                       | Regex, Range & Base58/Bech32 Chk  |
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------------------------+
                       | DUCKDB LOCAL ANALYTICAL DATABASE  |
                       | In-process 14-table OLAP Store    |
                       +--------+-----------------+--------+
                                |                 |
            +-------------------+                 +-------------------+
            |                                                         |
            v                                                         v
+---------------------------------------+ +---------------------------------------+
| CORRELATION ENGINE                    | | NETWORKX GRAPH TOPOLOGY               |
| Correlates Network <-> Ledger Layer   | | IP -> TXID -> Wallet Bipartite Graph  |
| IP_TO_TXID, TXID_TO_WALLET, etc.      | | PageRank, Centrality, Degree Metrics  |
+-------------------+-------------------+ +-------------------+-------------------+
                    |                                         |
                    +--------------------+--------------------+
                                         |
                                         v
                       +-----------------------------------+
                       | DETERMINISTIC FEATURE ENGINEERING |
                       | 19 Behavioral & Topological Feats |
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------------------------+
                       | UNSUPERVISED ML PIPELINE          |
                       | Isolation Forest + DBSCAN Cluster |
                       | 0-100 Standardized Risk Scoring   |
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------------------------+
                       | EVIDENCE GENERATION ENGINE        |
                       | Baseline Deviation Ratios (e.g 40x|
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------------------------+
                       | LOCAL OLLAMA + NVIDIA NEMOTRON 3.5|
                       | Zero-Hallucination Explanations   |
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------------------------+
                       | FASTAPI BACKEND + REACT DASHBOARD |
                       | Link Analysis, Timeline, Dossiers |
                       +-----------------------------------+
```

---

## 2. Core Subsystems

### Ingestion & Validation
- Standardizes diverse incoming network captures and blockchain dumps.
- Immutably captures raw payloads with validation statuses (`VALID`, `INVALID`) in `raw_records`.
- Validates IPv4/IPv6 syntax, ports (1-65535), timestamps, 64-hex TXIDs, and Base58/Bech32 address formatting.

### Columnar Storage (DuckDB)
- 14 optimized relational tables indexed for rapid multi-hop link exploration.
- 100% in-process with zero external server dependencies.

### Unsupervised Anomaly Detection
- Leverages `sklearn.ensemble.IsolationForest` without requiring labeled training datasets.
- Maps decision function scores into a transparent 0-100 `normalized_risk_score`.
- Assigns clear forensic severities: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.

### Local AI Reasoning (Ollama + NVIDIA Nemotron)
- Strictly bounds generation to verified database evidence.
- Explains leads without fabricating transactions, IPs, or altering scores.

# SIH26146 — AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

[![Organization](https://img.shields.io/badge/Organization-NTRO-blue.svg)](https://ntro.gov.in)
[![Category](https://img.shields.io/badge/Category-Software-green.svg)]()
[![Theme](https://img.shields.io/badge/Theme-Blockchain%20%26%20Cybersecurity-orange.svg)]()
[![Offline Mode](https://img.shields.io/badge/Operation-100%25%20Offline-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

An offline, air-gapped investigation-support platform developed for the **National Technical Research Organisation (NTRO)** under Smart India Hackathon 2026 (Problem Statement SIH26146).

The system correlates network-layer observations (IP addresses, ports, timestamps) with blockchain-layer ledger data (TXIDs, wallet addresses, input/output amounts, fees, scripts), extracts 19 deterministic behavioral metrics, detects anomalies using unsupervised Machine Learning (**Isolation Forest** and **DBSCAN**), generates mathematical evidence, and synthesizes structured briefings via a local **NVIDIA Nemotron 3.5 Lightning** model running through **Ollama**.

---

## Key Capabilities

- **100% Offline & Air-Gap Ready**: Zero external cloud APIs, zero CDN script tags, zero internet dependencies.
- **Multi-Format Ingestion**: Ingests and validates CSV, JSON, and XML metadata payloads.
- **Transparent Evidence Engine**: Every alert includes exact mathematical deviations against population medians (e.g. 40x burst, 14 IPs).
- **Unsupervised ML Pipeline**: Isolation Forest and DBSCAN entity clustering without requiring labeled criminal training data.
- **Local NVIDIA AI Reasoning**: Integrates Ollama with `nemotron-3.5-lightning` to summarize evidence and answer investigator questions without hallucination.
- **Interactive Link Analysis Dashboard**: Modern React + Vite + Tailwind dashboard with interactive canvas graph topology and investigation timeline.

---

## System Architecture

```
DATASET (CSV/JSON/XML)
  ↓
STRICT VALIDATION & DEDUPLICATION (Regex, Ports, Base58/Bech32)
  ↓
LOCAL DUCKDB COLUMNAR STORAGE (14 Analytical Tables)
  ↓
CORRELATION ENGINE (IP <-> TXID <-> Wallets)
  ↓
NETWORKX ENTITY GRAPH (Topological Centrality & Degree)
  ↓
FEATURE ENGINEERING (19 Deterministic Behavioral Metrics)
  ↓
ISOLATION FOREST ANOMALY DETECTION (0-100 Risk Scoring)
  ↓
DETERMINISTIC EVIDENCE ENGINE (Population Baseline Deviations)
  ↓
LOCAL OLLAMA + NVIDIA NEMOTRON 3.5 (Structured Explainable Leads)
  ↓
FASTAPI REST API + REACT INVESTIGATION DASHBOARD
```

---

## Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- Node.js 20+ (for building frontend)
- Git

### 2. Installation
```bash
# Clone repository
cd sih26146

# Install backend dependencies
pip install -r backend/requirements.txt

# Build offline frontend bundle
cd frontend
npm ci
npm run build
cd ..
```

### 3. Initialize Database & Generate Benchmark Data
```bash
# Initialize DuckDB analytical schema (14 tables)
python scripts/init_database.py --reset

# Generate synthetic benchmark datasets (CSV, JSON, XML)
python scripts/generate_demo_data.py

# Ingest benchmark metadata into database
python scripts/run_ingest.py data/sample/synthetic_demo.csv
```

### 4. Launch Application
```bash
cd backend
python run.py
```
Open your browser at: **`http://localhost:8000/`**.

---

## Verification & Testing

### Run Complete Automated Test Suite (12 Tests)
```bash
python -m pytest backend/tests/ -v
```

### Run 100% Offline Compliance Verification
```bash
python scripts/test_offline.py
```

---

## Local NVIDIA AI Setup (Ollama)

1. Install [Ollama](https://ollama.com).
2. Pull and run NVIDIA Nemotron 3.5 Lightning:
   ```bash
   ollama run nemotron-3.5-lightning
   ```
3. The SIH26146 backend automatically detects Ollama running on `http://localhost:11434`. If Ollama is not active, the system automatically falls back to its internal deterministic forensic reasoning engine without downtime.

---

## Docker Deployment (Linux)

```bash
docker compose up -d --build
```
Access the dashboard at `http://localhost:8000/`.

---

## Project Structure

```
sih26146/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI REST endpoints
│   │   ├── correlation/  # Metadata correlation engine
│   │   ├── database/     # DuckDB connection & 14-table schema
│   │   ├── features/     # 19-metric behavioral extractor
│   │   ├── graph/        # NetworkX entity graph topology
│   │   ├── ingestion/    # CSV, JSON, XML ingestion pipeline
│   │   ├── llm/          # OllamaProvider (NVIDIA Nemotron)
│   │   ├── ml/           # Isolation Forest & DBSCAN
│   │   ├── services/     # Evidence engine & alert dossiers
│   │   └── utils/        # Strict regex & validation rules
│   ├── tests/            # Pytest integration test suite
│   ├── requirements.txt
│   └── run.py
├── frontend/             # React + Vite + Tailwind dashboard
├── data/
│   ├── database/         # sih26146.duckdb analytical database
│   ├── raw/              # Uploaded raw datasets
│   └── sample/           # Synthetic demo datasets (CSV, JSON, XML)
├── docker/
├── docs/                 # Complete architectural & operational guides
├── scripts/              # Ingestion, inspection, ML, and offline tests
├── docker-compose.yml
├── .env.example
├── README.md
└── LICENSE
```

---

## License & Attribution
Developed for Smart India Hackathon 2026 — Problem Statement SIH26146.  
Organization: National Technical Research Organisation (NTRO).  
Licensed under the Apache License, Version 2.0.

# SIH26146 REST API Documentation

All endpoints return structured JSON and operate locally under the `/api` prefix.

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | System health check (DuckDB and Ollama readiness) |
| `GET` | `/api/statistics` | High-level metrics, anomaly distribution, hourly volume |
| `POST` | `/api/ingest` | Uploads and normalizes CSV, JSON, or XML metadata |
| `POST` | `/api/analyze` | Executes Feature Engineering, Isolation Forest, and Alert Generation |
| `GET` | `/api/transactions` | Paginated list of blockchain transactions |
| `GET` | `/api/transaction/{txid}` | Full transaction dossier (inputs, outputs, network broadcasts) |
| `GET` | `/api/wallets` | Paginated list of wallets with risk scores and volumes |
| `GET` | `/api/wallet/{wallet_address}` | Wallet profile with features, counterparties, and linked alerts |
| `GET` | `/api/ips` | Monitored IP addresses with geo-country and broadcast counts |
| `GET` | `/api/ip/{ip_address}` | IP broadcast history and associated transactions |
| `GET` | `/api/entities` | Universal entity registry (`WALLET`, `IP`, `TXID`) |
| `GET` | `/api/entity/{entity_id}` | Entity relationships and outgoing links |
| `GET` | `/api/graph/{entity_id}` | k-hop neighborhood subgraph formatted for link analysis |
| `GET` | `/api/alerts` | Ranked investigation alert queue with filter parameters |
| `GET` | `/api/alerts/{alert_id}` | Complete investigative dossier with exact mathematical evidence |
| `PATCH` | `/api/alerts/{alert_id}/status` | Updates analyst status (`NEW`, `INVESTIGATING`, `REVIEWED`, `DISMISSED`) |
| `POST` | `/api/explain/{alert_id}` | Triggers local NVIDIA Nemotron synthesis of the alert evidence |
| `POST` | `/api/alerts/{alert_id}/ask` | Interactive Q&A on stored evidence with local AI |

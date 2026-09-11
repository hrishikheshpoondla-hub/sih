# SIH26146 Deployment Guide (Linux & Cross-Platform)

**Organization**: National Technical Research Organisation (NTRO)  
**Target Environment**: Linux (Ubuntu 22.04 / 24.04 LTS, Debian, RHEL) & Docker

---

## 1. Quick Start via Docker Compose
To deploy the full application with the local database and Ollama service:

```bash
# Clone or navigate to the repository
cd sih26146

# Start containers in detached mode
docker compose up -d --build

# Inspect running services
docker compose ps

# Access the Investigation Dashboard
# Open browser at: http://localhost:8000/
```

---

## 2. NVIDIA GPU Acceleration for Ollama (Nemotron 3.5)
To accelerate `nemotron-3.5-lightning` inference on Linux with NVIDIA GPUs:

1. Install NVIDIA Container Toolkit:
   ```bash
   sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```
2. In `docker-compose.yml`, uncomment the `deploy.resources.reservations.devices` section under `ollama`.
3. Pull the Nemotron model locally:
   ```bash
   docker exec -it sih26146-ollama ollama pull nemotron-3.5-lightning
   ```

---

## 3. Standalone Native Linux Installation (Without Docker)

### Prerequisites:
- Python 3.11+
- Node.js 20+

### Setup Steps:
```bash
# 1. Install Python Dependencies
pip install -r backend/requirements.txt

# 2. Initialize Analytical Database
python scripts/init_database.py --reset

# 3. Generate Benchmark Synthetic Datasets
python scripts/generate_demo_data.py

# 4. Ingest Benchmark Data
python scripts/run_ingest.py data/sample/synthetic_demo.csv

# 5. Build Offline Frontend Assets
cd frontend
npm ci
npm run build
cd ..

# 6. Run FastAPI Server (serves both API and compiled dashboard)
cd backend
python run.py
```
Open `http://localhost:8000/` in your browser.

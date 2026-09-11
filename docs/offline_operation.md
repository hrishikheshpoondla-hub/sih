# SIH26146 Offline Operation & Air-Gap Guide

## Air-Gap & Disconnected Environment Guarantee
SIH26146 is engineered specifically for secure, air-gapped forensic environments utilized by defence, cybersecurity, and intelligence agencies like NTRO.

### Key Architectural Protections:
1. **Zero External Cloud AI**:
   - The LLM layer uses **Ollama** running locally on `localhost:11434` loading **NVIDIA Nemotron 3.5 Lightning**.
   - No data or prompts ever leave the local host.
   - When Ollama is offline or unavailable, the system automatically uses an internal deterministic forensic reasoning engine without errors.
2. **Local Analytical Storage (DuckDB)**:
   - Columnar database stored as a single local file: `data/database/sih26146.duckdb`.
   - Requires no external database servers, background network ports, or credentials.
3. **Bundled Self-Contained Frontend**:
   - React + Tailwind + Lucide icons are compiled into static assets in `frontend/dist`.
   - Zero dependencies on external CDNs (no Google Fonts, unpkg, cdnjs, or remote map tiles).
4. **Offline Validation Test**:
   Execute the automated offline test suite to verify disconnected readiness:
   ```bash
   python scripts/test_offline.py
   ```

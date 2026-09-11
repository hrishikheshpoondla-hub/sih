# SIH26146 Local AI Reasoning Engine (Ollama + NVIDIA Nemotron)

## Model Configuration
- **Host**: Local Ollama runtime (`http://localhost:11434`)
- **Default Model**: `nemotron-3.5-lightning` (30B MoE with 3B active parameters)
- **Zero-Cloud Guarantee**: No external internet access or third-party cloud LLM APIs are contacted.

---

## Strict Guardrails & Zero-Hallucination Framework

### Rule 1: Evidence Boundary Injection
The LLM is prompted strictly with verified forensic facts fetched directly from DuckDB:
- Entity value & type
- Machine learning risk score and statistical confidence
- Mathematical baseline deviation ratios (e.g. `40.0x burst`, `14 IPs`)
- Exact recent transaction hashes and observed network IPs

### Rule 2: Anti-Fabrication Constraints
The system prompt strictly forbids:
- Inventing wallet addresses or transaction hashes
- Altering the mathematical anomaly score
- Claiming criminal guilt (mandating objective terms: 'anomalous', 'suspicious lead', 'investigative evidence')

### Rule 3: Offline Standby Fallback
If Ollama is temporarily stopped or compiling models, the system seamlessly transitions to a local deterministic forensic reasoning engine, ensuring uninterrupted analytical availability.

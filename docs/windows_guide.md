# SIH26146 Windows User & Developer Guide

**Organization**: National Technical Research Organisation (NTRO)  
**Operating System**: Windows 10 / 11 (64-bit)

---

## 1. Quick Start (One-Click)
Simply double-click or run from Command Prompt / PowerShell:
```cmd
start_windows.bat
```
or via PowerShell:
```powershell
.\start_windows.ps1
```
This automatically:
1. Verifies the Python runtime.
2. Initializes the local DuckDB database (`data/database/sih26146.duckdb`) if needed.
3. Loads the benchmark transactions.
4. Starts the local FastAPI server.
5. Launches your default web browser to: **`http://localhost:8000/`**.

---

## 2. Windows Environment Verification
To verify the system on Windows at any time:
```cmd
run_tests_windows.bat
```
This executes:
- The 12-test automated integration suite in `backend/tests/`.
- The 100% offline compliance audit in `scripts/test_offline.py`.

---

## 3. Local NVIDIA Ollama Setup on Windows
To enable the NVIDIA Nemotron 3.5 Lightning local LLM:
1. Download and install **Ollama for Windows** from [ollama.com/download/windows](https://ollama.com/download/windows).
2. Open a new terminal and run:
   ```cmd
   ollama run nemotron-3.5-lightning
   ```
3. Once running, the dashboard's **Local AI Reasoning** box will automatically use the local Nemotron model to generate explanations and answer investigator questions.
4. *Note: If Ollama is not running, the dashboard continues functioning with its built-in offline forensic reasoning engine.*

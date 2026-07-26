# P2P Cloud Gaming & Compute Marketplace

Decentralized marketplace for computing resources — matching idle GPU Providers with Consumers for low-latency cloud gaming and high-throughput batch compute.

## Project Structure

- `orchestrator/` — Central control plane API (FastAPI) handling matching, catalog, and auth.
- `agent/` — Provider Agent daemon running on GPU host nodes.
- `docs/` — Specifications, architectural decision records (ADRs), and task breakdown (`docs/Tasks/tasks.md`).

## Quick Start (Milestone M0)

### 1. Prerequisites
- Python 3.11+
- Docker Desktop (for local Postgres DB)

### 2. Start PostgreSQL Database
```powershell
docker compose up -d
```

### 3. Run the Orchestrator
```powershell
cd orchestrator
# Set up venv if not already done
python -m venv env
.\env\Scripts\activate
pip install -r requirements.txt

# Run server
python main.py
```
Orchestrator health check will be available at `http://localhost:8000/health`.

### 4. Run the Provider Agent Ping
```powershell
cd agent
# In a separate terminal
python main.py
```
The agent reads `ORCHESTRATOR_URL` from `.env`, pings the orchestrator's `/health` endpoint, and logs the result.

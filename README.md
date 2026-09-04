# Eucast MIC Breakpoint Interpreter

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## What It Does

EUCAST / CLSI Antimicrobial MIC Breakpoint Interpreter
Classifies Minimum Inhibitory Concentration (MIC) into Susceptible (S), Intermediate/Susceptible Increased Exposure (I), Resistant (R).

Zero-dependency Python implementation with single and batch evaluation.
Author: Dr. Abu Suraih Sakhri
License: MIT

---

## Key Capabilities & Algorithmic Modules

### Analytical Functions

- **`calculate_metrics()`**: Core domain algorithm that evaluates antimicrobial measurements and returns classification with clinical recommendation.
- **`process_single()`** — evaluates a single case via CLI arguments.
- **`process_batch()`** — processes CSV input files with path-traversal protection and outputs enriched results.
- **`main()`** — CLI entry point with subcommands for `single` and `batch` operations.

### Enterprise Agent System (`agents/`)

- **`supervisor.py`** — Master orchestrator coordinating multi-worker evaluations.
- **`workers.py`** — Specialized domain workers (InvariantQC, SafetyEscalation, ProtocolConformance).
- **`base.py`** — PHI Outbound Guard, HMAC-SHA256 tamper-evident audit trail.
- **`models.py`** — Pydantic v2 schemas for task payloads, alerts, and consensus dossiers.
- **`llm_factory.py`** — Pluggable LLM adapter (mock, Ollama, Claude, OpenAI).
- **`learning.py`** — Active learning Bayesian calibration engine.
- **`metrics.py`** — Prometheus operational metrics exporter.
- **`streamer.py`** — WebSocket telemetry broadcaster.
- **`api.py`** — FastAPI REST endpoints.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/eucast-mic-breakpoint-interpreter.git
cd eucast-mic-breakpoint-interpreter

# Install dependencies
pip install -e ".[test]"
```

### Environment Variables

| Variable | Description | Required |
|:---------|:------------|:---------|
| `AUDIT_SECRET_KEY` | Secret key for HMAC-SHA256 audit trail signing | Recommended (random key generated if unset) |
| `MODEL_PROVIDER` | LLM provider: `mock`, `ollama`, `claude`, `openai` | No (default: `mock`) |

---

## Usage

### Single Evaluation

```bash
python eucast_interpreter.py single --v1 14.5 --v2 4.2 --v3 1.8
```

### Batch CSV Processing

```bash
python eucast_interpreter.py batch -i sample.csv -o results.csv
```

### Enterprise CLI (`cli.py`)

```bash
# Single task audit
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Batch processing
python cli.py batch -i sample.csv -o results.csv

# Supervisory chat
python cli.py chat "Explain breakpoint classification"

# Verify audit trail integrity
python cli.py verify-audit

# Launch REST API server
python cli.py serve --host 127.0.0.1 --port 8000
```

### REST API

```bash
# Start server
python cli.py serve

# Health check
curl http://localhost:8000/health

# Prometheus metrics
curl http://localhost:8000/metrics

# Submit task evaluation
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{"task-id":"TASK-001","target-identifier":"KEY-01","primary_metric":14.5,"secondary_metric":4.2,"status_descriptor":"NOMINAL"}'
```

---

## Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `Patient_ID` | Patient identifier or observation key | Required |
| `v1` | Primary measurement or parameter value | Required |
| `v2` | Secondary measurement or parameter value | Required |
| `v3` | Tertiary measurement or parameter value | Required |

---

## Security

* **Zero-PHI Outbound Interceptor:** Active regex inspection blocking SSNs, MRNs, phone numbers, emails, patient names, and DOB patterns.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Path Traversal Protection:** All file I/O operations validate paths against traversal attacks.
* **Secure Key Generation:** Cryptographically random audit key generated when `AUDIT_SECRET_KEY` is not set (with development warning).
* **Input Validation:** CSV headers validated, null bytes rejected.

---

## Testing

```bash
# Run all tests
pytest -v

# Run specific test modules
pytest tests/test_security_and_validation.py -v
pytest tests/test_enrichment.py -v

# Run simulation benchmark
python simulator.py 100
```

---

## Container Deployment

```bash
docker build -t eucast-mic-breakpoint-interpreter .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret-key eucast-mic-breakpoint-interpreter
```

Or with docker-compose:

```bash
docker-compose up -d
```

---

## Project Structure

```
├── agents/                      # Enterprise agent system
│   ├── __init__.py
│   ├── api.py                   # FastAPI REST endpoints
│   ├── base.py                  # PHI Guard, Audit Trail, Security
│   ├── learning.py              # Bayesian calibration engine
│   ├── llm_factory.py           # LLM provider adapter
│   ├── metrics.py               # Prometheus metrics exporter
│   ├── models.py                # Pydantic data schemas
│   ├── streamer.py              # WebSocket telemetry
│   ├── supervisor.py            # Master orchestrator
│   └── workers.py               # Domain worker agents
├── tests/                       # Test suite
│   ├── test_enrichment.py
│   ├── test_eucast_mic_breakpoint_interpreter.py
│   └── test_security_and_validation.py
├── eucast_interpreter.py        # Core interpreter (single/batch)
├── cli.py                       # Enterprise CLI entry point
├── enrichment.py                # Enrichment engine suite
├── simulator.py                 # High-throughput stress testing
├── pyproject.toml               # Project configuration
├── Dockerfile                   # Container build
├── docker-compose.yml           # Container orchestration
├── sample.csv                   # Sample input data
└── benchmark_dataset.json       # Golden benchmark test cases
```

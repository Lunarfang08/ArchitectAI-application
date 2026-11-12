<div align="center">

# ARCHITECT<span style="color:#8b5cf6">AI</span>

### Your architecture team. On your machine. Under your control.

**A local-first AI engineering studio that turns rough requirements into grounded system designs, reviewable starter repositories, code reviews, tests, and future-impact simulations.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](backend/pyproject.toml)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)](frontend/package.json)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](backend/app/main.py)
[![Ollama](https://img.shields.io/badge/Ollama-local_AI-111111)](https://ollama.com/)
[![CI](https://img.shields.io/badge/Azure_Pipelines-ready-0078D4?logo=azurepipelines&logoColor=white)](azure-pipelines.yml)
[![License](https://img.shields.io/badge/license-proprietary-E11D48)](#license)

[Launch locally](#quick-start) · [See the system](#inside-the-machine) · [Read the docs](docs/architecture.md) · [Deploy](docs/deployment.md)

</div>

![ArchitectAI product interface](frontend/public/architect-ai-hero.png)

ArchitectAI is an approval-gated engineering workspace for software design, project generation, code review, and system resilience analysis. Project data and the default model runtime stay local.

## The flex

| Capability | What it does | Guardrail |
| --- | --- | --- |
| **Architecture design** | LangGraph prepares a request for one configured model call | No browsing or shell tools |
| **Grounded local RAG** | Upload Markdown, TXT, JSON, YAML, or CSV and retrieve relevant ChromaDB chunks | Offline deterministic embeddings; no hosted API |
| **Streaming workspace** | Streams sanitized GitHub-Flavored Markdown over SSE and persists every conversation | Interrupted responses are marked incomplete |
| **Project generation** | Converts an approved architecture into a complete, staged file manifest | Review first; explicit approval writes files |
| **Code review + test design** | Produces structured findings and proposes test files from staged source | Reads text only; never executes generated code |
| **Future Lab** | Simulates component impact, failures, scores, and repair proposals | Predictions are labeled estimates and never modify files |
| **Optional cloud services** | Can use Azure OpenAI and query an existing Azure AI Search index | Disabled by default; never provisions resources |

Everything important is visible before it becomes real. That is the point.

## Quick start

### 01 — Bring your model

Install and start [Ollama](https://ollama.com/), then pull at least the lightweight fallback model:

```bash
ollama pull qwen2.5:3b
```

For stronger code output, also pull the default model:

```bash
ollama pull qwen2.5-coder:7b
```

### 02 — Boot ArchitectAI

You need Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 22+, npm, and Git.

```bash
git clone YOUR_REPOSITORY_URL architect-ai
cd architect-ai
cp .env.example .env
make setup
```

Run the services in two terminals:

```bash
# terminal 1 — API
make dev-backend
```

```bash
# terminal 2 — interface
make dev-frontend
```

Open **http://localhost:3000** for the cinematic landing page or **http://localhost:3000/workspace** to start building. Interactive API docs live at **http://127.0.0.1:8000/docs**.

### Docker, if that is your love language

Start Ollama on the host first. Docker does not download models for you.

```bash
cp .env.example .env
make docker-up
```

```bash
make docker-logs   # follow both services
make docker-down   # stop; persistent volumes survive
```

The Compose stack binds ports to loopback only and keeps the database, knowledge base, and generated projects in separate named volumes.

## Try it like you mean it

Paste this into the workspace:

```text
Design a multi-tenant fleet maintenance platform for 50,000 vehicles.

Constraints:
- event-driven work-order processing
- offline-first mobile inspections
- regional data residency
- auditable role-based access
- an incremental migration from a legacy PostgreSQL application

Return the system boundaries, core data model, API strategy, deployment topology,
failure modes, security controls, observability plan, and a delivery roadmap.
```

Then move through the studio:

1. Generate and inspect the architecture.
2. Add your own knowledge files for grounded follow-up questions.
3. Stage a starter repository and review every proposed path.
4. Approve the write only when the manifest looks right.
5. Run code review, stage tests, or open **Future Lab** to stress the design.

Example prompts and knowledge packs are in [`examples/prompts`](examples/prompts/) and [`examples/knowledge`](examples/knowledge/).

## API, minus the mystery

Check database readiness without waking the model:

```bash
curl --fail http://127.0.0.1:8000/api/v1/ready
# {"status":"ready"}
```

Inspect the complete runtime—including Ollama, Azure, AutoGen, LangGraph, and the knowledge base:

```bash
curl --silent http://127.0.0.1:8000/api/v1/health | python -m json.tool
```

Explore and execute the typed API at `http://127.0.0.1:8000/docs`. Architecture streams use Server-Sent Events, so progress and model output arrive without waiting for a monolithic response.

## Inside the machine

```text
                         ┌──────────────────────────────┐
                         │       Next.js 16 studio      │
                         │ workspace · trace · approval │
                         └──────────────┬───────────────┘
                                        │ REST + SSE
                         ┌──────────────▼───────────────┐
                         │          FastAPI API         │
                         └───────┬────────┬────────┬────┘
                                 │        │        │
                    ┌────────────▼─┐  ┌───▼────┐  ┌▼────────────────┐
                    │  LangGraph   │  │ SQLite │  │ Local ChromaDB  │
                    │ orchestration│  │ state  │  │ grounded RAG    │
                    └──────┬───────┘  └────────┘  └─────────────────┘
                           │
                    ┌──────▼───────┐       optional, explicit opt-in
                    │ AutoGen agent│──────────────┬───────────────────
                    │   runtime    │              │
                    └──────┬───────┘       ┌──────▼──────────┐
                           │               │ Azure OpenAI    │
                    ┌──────▼───────┐       │ + AI Search    │
                    │ Local Ollama │       └─────────────────┘
                    └──────────────┘
```

FastAPI owns orchestration and safety policy. The Next.js application is a typed interface, not a second backend. Provider boundaries keep the free local path separate from optional cloud integrations. Read the full [architecture notes](docs/architecture.md) for workflow and persistence details.

## Local by default. Deliberately.

- No paid or hosted model API is required.
- Azure integrations are off until you explicitly enable and configure them.
- Uploaded documents use local ChromaDB and offline embeddings.
- Model HTML is sanitized before rendering.
- Generated paths are checked for traversal, absolute paths, secrets, oversized output, and unsafe directories.
- Generation, test writing, and future repairs have separate human checkpoints.
- ArchitectAI does **not** execute generated applications, package managers, shells, or tests.
- `.env`, databases, uploads, generated projects, and credentials must never be committed.

This is a single-user local workspace. Do not expose it publicly without adding authentication, authorization, TLS, rate limiting, and a production data-store strategy.

## Configuration that matters

The checked-in [`.env.example`](.env.example) documents every setting. These are the usual knobs:

```dotenv
MODEL_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_FALLBACK_MODEL=qwen2.5:3b
MODEL_MAX_OUTPUT_TOKENS=1000
ARCHITECTURE_GENERATION_TIMEOUT_SECONDS=0
AUTOGEN_EXPERIMENTAL_ENABLED=true
LANGGRAPH_ORCHESTRATION_ENABLED=true
AZURE_INTEGRATIONS_ENABLED=false
```

`ARCHITECTURE_GENERATION_TIMEOUT_SECONDS=0` allows a healthy stream to finish naturally; the Stop action still cancels it. Restart the backend after changing environment values.

To use Azure OpenAI, explicitly enable Azure, supply the endpoint/key/deployment values, and set `MODEL_PROVIDER=azure_openai`. Azure services may cost money. ArchitectAI never creates an Azure resource for you.

## Quality gates

```bash
make lint
make test
cd frontend && npm run build
```

The Azure DevOps pipeline runs locked installs, linting, isolated tests, a fresh migration check, the production frontend build, container builds, and readiness smoke tests. It uses fake model providers in tests and does not deploy or push images.

## Repository map

```text
architect-ai/
├── backend/              FastAPI, agents, persistence, migrations, tests
├── frontend/             Next.js product site and engineering workspace
├── docs/                 architecture, deployment, runtime notes
├── examples/             sample prompts and project knowledge packs
├── compose.yaml          hardened local two-service stack
├── azure-pipelines.yml   CI validation pipeline
├── Makefile              setup, development, quality, and Docker shortcuts
└── .env.example          safe configuration template
```

## Product status

ArchitectAI is active, pre-release software. The implemented surface includes persistent workspaces, streaming model runs, the LangGraph/AutoGen workflow, grounded local knowledge, approval-gated generation, code review, test design, Future Lab, Docker packaging, and CI validation.

## License

**Proprietary and confidential — source available for evaluation only.**

Copyright © 2026. All rights reserved. Public visibility of this repository does not grant permission to copy, modify, distribute, sublicense, sell, host, or create derivative works from the software. No license is granted except by a separate written agreement with the copyright owner.

If you intend to accept outside contributions or offer an open-source edition, add the appropriate license and contribution policy first. Until then: look, learn, and please do not lift.

---

<div align="center">

**ArchitectAI** · serious systems, zero cloud dependency, absolutely no mystery writes.

</div>

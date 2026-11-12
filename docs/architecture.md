# Architecture

## Local runtime

```text
Next.js dashboard
        |
        | REST + Server-Sent Events
        v
FastAPI application
        |
        +-- Ollama model provider
        +-- LangGraph request preparation and architecture generation
        +-- ChromaDB retrieval with offline deterministic embeddings
        +-- SQLite metadata and checkpoints
        +-- Restricted generated-project storage
```

FastAPI owns application behavior. Next.js is a typed user interface and does not duplicate backend orchestration. Provider interfaces will keep local implementations separate from future optional Azure implementations.

## Architecture generation

LangGraph prepares the request and passes it to one configured model call:

```text
requirement → LangGraph preparation → Architect → streamed Markdown response
```

The architecture response is streamed to the workspace. When enabled, AutoGen runs the model
call through an `AssistantAgent`; otherwise the configured provider streams directly. The
generation, code review, and test design actions use separate bounded agents and require approval
before writing files. These workflows do not execute code, browse, or make external changes.

See [AutoGen runtime notes](autogen-experiment.md) for configuration and limitations.

## Persistent workspace

Projects contain conversations, and conversations contain ordered user and assistant messages.
SQLAlchemy provides the async data layer, Alembic owns schema migrations, and SQLite stores
all records locally. Streaming responses are saved with explicit `streaming`, `completed`,
`cancelled`, or `failed` state so an interrupted result is never presented as complete.

The dashboard renders model output as sanitized GitHub-Flavored Markdown. Raw model HTML is
not executed, and source-code blocks are presentation-only.

## Project knowledge

The knowledge base accepts bounded UTF-8 TXT, Markdown, JSON, YAML, and CSV uploads. Documents are
split into overlapping chunks and indexed in local ChromaDB using deterministic token-hash vectors;
ingestion does not download an embedding model or contact a hosted service. Before each chat run,
the most relevant chunks are added to the agent input with filename provenance. Raw uploads are not
executed, and unsupported or binary files are rejected.

## Project generation

After an architecture response is complete, a dedicated AutoGen agent proposes a structured file
manifest. The backend rejects absolute paths, traversal, duplicates, oversized output, lockfiles,
credential-like files, and dependency/build directories. The manifest is stored as `staged` and is
visible in the dashboard before any files are created. A separate approval request atomically writes
the reviewed files beneath `GENERATED_PROJECTS_DIR/<project-id>/`; existing output is never
overwritten and generated programs are never executed.

## Code review and test design

A dedicated AutoGen Code Reviewer inspects the staged manifest as text and returns bounded,
structured findings with severity, file provenance, and remediation advice. A separate Test
Designer consumes the manifest and review to propose test source files. Test paths must be
recognizable test locations, cannot overwrite project files, and remain staged until explicit
approval writes them inside the already-approved generated project. Neither agent executes code,
test runners, package managers, shells, or generated applications.

## Optional Azure adapters

The default remains the zero-cost Ollama and ChromaDB path. With
`AZURE_INTEGRATIONS_ENABLED=true` and complete credentials, `MODEL_PROVIDER=azure_openai` selects
an Azure OpenAI v1 streaming adapter for chat. AutoGen uses its OpenAI client against the unified
Azure v1 endpoint when enabled. A separate Azure
AI Search adapter can query an existing index through `/api/v1/azure/search`, but local knowledge
ingestion continues to use ChromaDB unless an Azure index is independently provisioned and loaded.
Status responses disclose configuration readiness but never return keys.

The OpenAI adapter follows Microsoft's unified Azure OpenAI v1 endpoint, while the search adapter
uses the Azure AI Search documents query API:

- [Azure OpenAI v1 migration guidance](https://learn.microsoft.com/en-us/azure/developer/ai/how-to/azure-openai-to-responses)
- [Azure AI Search REST API versions](https://learn.microsoft.com/en-us/rest/api/searchservice/search-service-api-versions)

## Local-to-Azure learning map

| Free local implementation | Optional Azure equivalent |
| --- | --- |
| Ollama | Azure OpenAI / Azure AI Foundry |
| ChromaDB | Azure AI Search |
| Local filesystem | Azure Blob Storage |
| Environment variables | Azure Key Vault |
| Structured local logs | Azure Monitor / Application Insights |
| Docker Compose | Azure Container Apps |

Azure services are not local emulators and will not be described as deployed until actual resources have been configured and verified.

## Deployment runtime

Docker Compose runs the FastAPI API and standalone Next.js server as unprivileged users,
with loopback-only published ports. Three named volumes persist SQLite, knowledge storage,
and generated projects. The backend applies Alembic migrations before starting Uvicorn.
Frontend startup depends on a database/schema readiness check, independent of Ollama's
availability. The model remains on the host; Azure stays disabled in the local stack.

The Azure DevOps pipeline validates both applications, fresh migrations, container builds,
and startup without live model calls. It does not provision resources, push images, or deploy.
See [Deployment and recovery](deployment.md).

## Safety boundary details

Generated source files will be constrained to an application-controlled project directory. ArchitectAI v1 generates and reviews tests but does not execute generated projects. Human approval checkpoints will be required before sensitive workflow transitions.


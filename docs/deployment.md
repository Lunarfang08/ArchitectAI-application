# Local deployment and CI

## Docker Desktop

Start Docker Desktop and Ollama on the host. Install a model with
`ollama pull qwen2.5:3b` if needed, then run `make docker-up` from the repository root.
Open http://localhost:3000. The API is at http://127.0.0.1:8000/docs.

The stack builds Python 3.11 and Node 22 images from their lockfiles. Both application
processes run as unprivileged users. Only loopback ports 3000 and 8000 are published.
The backend migrates its database before starting; the frontend waits for database readiness.
`/api/v1/ready` checks the schema without calling Ollama. `/api/v1/health` additionally
reports model availability; a degraded model does not prevent browsing saved projects.

Compose connects to host Ollama using `host.docker.internal:11434`. On Linux, Ollama must
listen on an interface reachable from the Docker bridge; restrict that interface with the
host firewall. Docker Desktop on macOS/Windows handles the host gateway automatically.
No model downloads are triggered by Compose. Azure is disabled in this local stack.

Use `make docker-logs` for logs and `make docker-down` to stop the stack. Stopping it
preserves the `database`, `knowledge`, and `generated` named volumes. These volumes are
separate from the files used by the native development setup. Do not run native services
and Compose on the same ports. Do not use `docker compose down --volumes` unless you intend
to permanently erase the container workspace.

Configuration interpolation reads the root `.env`; only the explicitly listed Compose
variables are passed into containers. Models and output token limits can be set there.
The browser API URL is embedded at frontend build time, so changing its address requires
rebuilding the frontend image. The supplied stack is intended for a single local user;
public hosting requires authentication and TLS before exposing these APIs.

## Backup and recovery

Stop the stack before taking a consistent backup. Back up all three named volumes together
using Docker Desktop's volume export tooling. Keep their project IDs and files together.
For native development, back up `backend/data`, `backend/knowledge_base`, and
`backend/generated_projects` with the processes stopped. Restore to the same deployment
mode, then start it and apply migrations. Store backups outside Git. Before an upgrade,
take a backup; rollback means restoring that backup with its matching application version.

## Azure DevOps CI

Create an Azure Pipeline from the repository and select `azure-pipelines.yml`. No Azure
subscription, model endpoint, service connection, registry, or paid API is needed for tests.
Hosted-agent availability and billing depend on your Azure DevOps organization.

The pipeline installs locked dependencies, lints both applications, runs isolated tests,
publishes JUnit results, builds Next.js, verifies a fresh migration against ORM metadata,
builds both images, and smoke-tests container readiness. Tests use fake model providers.
Images are built locally on the agent; they are not pushed and nothing is deployed.
For Azure Repos, configure build validation on the main branch; YAML PR triggers apply to
supported GitHub/Bitbucket repositories. Actual hosted pipeline execution must be checked
in your connected Azure DevOps organization.

## Troubleshooting

- Docker socket unavailable: start Docker Desktop and wait for its engine to become ready.
- Port already allocated: stop the native frontend/backend before `make docker-up`.
- Model unavailable: check `ollama list` and the backend's `OLLAMA_BASE_URL` connectivity.
- Container unhealthy: inspect `docker compose logs backend`; database permissions and
  migration failures are reported before the API starts.
- Future Lab locked: select a saved project with a completed architecture, or use its
  **Open Architecture studio** action. A new workspace has no architecture to simulate.
- Truncated simulation output: raise `MODEL_MAX_OUTPUT_TOKENS` (Compose defaults to 4096)
  and use a model that follows structured JSON output. Invalid output is not saved.

Architecture generation has no overall deadline by default
(`ARCHITECTURE_GENERATION_TIMEOUT_SECONDS=0`). The stream sends a heartbeat every 15 seconds
while waiting for model output, and Stop still cancels the model task. A positive value
opts into a total deadline. `OLLAMA_REQUEST_TIMEOUT_SECONDS=600` controls direct-provider
network inactivity; AutoGen's Ollama client uses its SDK transport defaults. An unavailable
or stalled provider can still fail. Restart the backend
after changing environment settings; for Docker, rebuild/recreate with `make docker-up`.
If an older environment explicitly sets the previous 150-second deadline, change it to 0.

## Verification

Run `make lint`, `make test`, and `cd frontend && npm run build` for native checks.
Run `docker compose config --quiet` and `make docker-up` for local container verification.
Check `/`, `/workspace`, `/api/v1/ready`, and `/api/v1/health`; restart the stack and verify
saved work remains. Model-backed generation additionally needs a working Ollama model.

Startup follows [Docker's health-based dependency ordering](https://docs.docker.com/compose/how-tos/startup-order/).
CI results use [Azure Pipelines JUnit publishing](https://learn.microsoft.com/en-us/azure/devops/pipelines/tasks/reference/publish-test-results-v2?view=azure-pipelines).

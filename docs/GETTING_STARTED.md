# Getting Started

## Prerequisites

- **Docker Desktop** (Mac/Windows) or **Docker Engine** + **Compose v2** (Linux)
- **GNU Make** (comes with macOS, `sudo apt install build-essential` on Ubuntu)
- Optional: Python 3.12 and Node 20 if you want to run tools outside Docker

Check:

```bash
docker --version            # Docker version 24+ recommended
docker compose version      # Compose version v2.x
make --version
```

## First-time setup

```bash
# 1. create your local .env
make init

# 2. add your Anthropic API key (optional — echo agent works without it)
$EDITOR .env
#   set ANTHROPIC_API_KEY=sk-ant-...

# 3. build and start everything
make up

# 4. verify it's alive
make smoke
```

You should see:

```
{"status":"ok"} — backend OK
{"status":"ready"} — backend ready
{"agents":["claude","echo"]}
```

And the UIs at:

- Frontend: <http://localhost:5173>
- Backend docs (Swagger): <http://localhost:8000/docs>

## Day-to-day workflow

### Start the stack
```bash
make up              # detached
make up-fg           # foreground (Ctrl-C to stop)
```

### Watch logs
```bash
make logs            # all services
make logs-backend    # just backend
```

### Run tests
```bash
make test            # everything
make test-backend    # just backend
make test-frontend   # just frontend
make test-backend-cov  # with coverage
```

### Format and lint
```bash
make format          # auto-fix
make lint            # check only
make check           # lint + tests (what CI would do)
```

### Stop the stack
```bash
make down            # stop, keep volumes
make nuke            # stop, delete volumes (DB data lost)
```

## Adding a new agent

1. Create `backend/src/app/agents/my_agent.py`:

```python
from app.agents.base import Agent, AgentRequest, AgentResponse


class MyAgent(Agent):
    name = "my_agent"

    async def run(self, request: AgentRequest) -> AgentResponse:
        # your logic here
        return AgentResponse(output="hello from MyAgent", agent=self.name)
```

2. Register it in `backend/src/app/agents/registry.py`:

```python
from app.agents.my_agent import MyAgent

_REGISTRY: dict[str, Agent] = {
    EchoAgent.name: EchoAgent(),
    ClaudeAgent.name: ClaudeAgent(),
    MyAgent.name: MyAgent(),   # <— add here
}
```

3. Add a test in `backend/tests/test_my_agent.py`.

4. No need to touch the router — it reads from the registry.

5. Restart the backend (`make restart`) and verify:
```bash
curl -X POST http://localhost:8000/api/v1/agents/my_agent/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "hello"}'
```

## Adding a Python dependency

1. Add it to `backend/pyproject.toml` under `dependencies`.
2. Mirror it in `backend/requirements.txt` (keeps the Dockerfile simple).
3. Rebuild: `make build-backend`.

## Adding a Node dependency

```bash
make shell-frontend
> npm install <package>
> exit
```

`package.json` and `package-lock.json` are mounted, so changes persist on the host.
Rebuild: `make build-frontend`.

## Troubleshooting

### Port already in use
Another service is on 5173/8000/5432/6379. Either stop it or edit
`docker-compose.dev.yml` to change the host port.

### Backend can't connect to the DB
The DB healthcheck may still be starting. `make logs-backend` to confirm.
The backend waits via `depends_on: condition: service_healthy`, so this is
usually only an issue if the DB init failed. Try `make nuke && make up`.

### `ModuleNotFoundError: app`
You're probably running pytest outside the container. Either:
- Run via `make test-backend` (recommended), or
- Install locally: `make install-backend`, then `cd backend && pytest`.

### Anthropic 401
`ANTHROPIC_API_KEY` is missing or invalid in `.env`. The `echo` agent still
works without it.

### Frontend hot-reload is slow
On Mac/Windows, volume mounts can be slow. Add `:cached` to the volume flag
in `docker-compose.dev.yml`, or run `npm run dev` directly on the host.

### "Docker daemon not running"
Start Docker Desktop. On Linux: `sudo systemctl start docker`.

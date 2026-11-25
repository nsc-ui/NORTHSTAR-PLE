## Docker (local container)

Prerequisites: Docker Engine with the Compose plugin.

1. Copy the safe configuration template:
   ```bash
   cp .env.example .env
   ```
2. Build and start the websocket server:
   ```bash
   docker compose up --build -d
   ```
3. Check status and logs:
   ```bash
   docker compose ps
   docker compose logs -f northstar
   ```
4. Stop it:
   ```bash
   docker compose down
   ```

The service listens on `ws://localhost:8000` by default (or the host port set by
`PLE_PORT`). The image runs as an unprivileged user. The container only packages
the NORTHSTAR WebSocket server; it does **not** install the official PLE kit,
run the official evaluator, grant gated dataset access, or provision the model
proxy. Those integrations require the official environment and credentials.

For local checks without starting the service:
```bash
docker build -t northstar-ple:local .
docker run --rm northstar-ple:local python scripts/check_entry.py
docker run --rm northstar-ple:local python tests_unit.py
docker run --rm northstar-ple:local python tests_context.py
docker run --rm northstar-ple:local python tests_cancel.py
docker run --rm northstar-ple:local python tests_smoke.py
```

Do not put tokens in the Dockerfile, image, or committed `.env`. When the
official proxy integration provides its credential mechanism, use its prescribed
secret injection. Docker Compose secrets are mounted as files under
`/run/secrets/<secret-name>` and should be preferred for supported integrations.

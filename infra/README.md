# Infrastructure Notes

## Architecture

```
[Attendees] ──HTTPS──► [Nginx / reverse proxy]
             │
           [FastAPI / uvicorn]
             │
           SQLite (attempts/stats)
             │
           [vLLM OpenAI API]
```

The repository currently supports two deployment modes:

1. External mode: run the app locally and point it at an already running OpenAI-compatible API such as Chat e-INFRA.
2. Slurm-managed vLLM mode: use `manager.py` to launch a split vLLM job and app job on the cluster.

## External Mode

This is the lightweight local workflow. The frontend is built locally and then served by the FastAPI app.

From the project root:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python manager.py start \
  --mode external \
  --port 8000 \
  --password changeme \
  --model mini
```

Useful commands:

```bash
python manager.py status
python manager.py restart-app
python manager.py logs --target app
python manager.py stop
```

Notes:

- Set `CHAT_EINFRA_URL=https://llm.ai.e-infra.cz/v1` and `CHAT_EINFRA_KEY=...` in `.env`.
- The configured endpoint must implement the OpenAI API; the backend probes `GET /v1/models` for health.
- `MODEL_NAME` must match a model identifier or alias exposed by the external API.
- You can still use `./infra/start.sh` if you prefer a simple foreground local run instead of `manager.py`.

## Slurm-Managed Deployment

This is the current cluster workflow.

From the project root:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python manager.py start \
  --mode vllm \
  --port 8642 \
  --password changeme \
  --model google/gemma-4-E4B-it \
  --gpus 1 \
  --gpuram 64G \
  --mem 32G \
  --app-mem 8G \
  --base-path /nlg/jailbreaking
```

Useful commands:

```bash
python manager.py status
python manager.py restart-app
python manager.py logs --target app
python manager.py logs --target vllm
python manager.py stop
```

Notes:

- `manager.py` tracks split jobs in `state.json` under `config`, `vllm`, and `app`.
- The app job is scheduled onto the same node as the vLLM job and talks to `http://127.0.0.1:8777/v1`.
- The managed vLLM launcher now uses `vllm serve ...` rather than `python -m vllm.entrypoints.openai.api_server`.
- Cluster startup can take a while because `vllm serve` may spend significant time compiling and warming the model before `/health` turns green.
- The Slurm scripts currently exclude `tdll-8gpu5`, which is known to fail ROCm/vLLM startup in this environment.

## Manual Backend + External API

```bash
# From project root
cp .env.example .env
# Edit .env with your values, then:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./infra/start.sh
```

In this mode, `infra/start.sh` builds the frontend and starts the FastAPI app on `127.0.0.1:8000`.

### Starting vLLM on the GPU Node

SSH into the GPU node and run:

```bash
vllm serve google/gemma-4-E4B-it \
  --host 0.0.0.0 \
  --port 8000 \
  --disable-log-requests
```

Then, on the web server, open the SSH tunnel so the backend can reach vLLM:

```bash
./infra/tunnel.sh user@gpunode
```

Set `CHAT_EINFRA_URL=http://localhost:8001/v1` in `.env`.

You can also point `.env` at any other OpenAI-compatible endpoint instead of using the tunnel script.

## Nginx Setup

1. Copy `infra/nginx.conf` to `/etc/nginx/sites-available/jailbreaking`
2. Update `root` path and `ssl_certificate` paths
3. Enable: `ln -s /etc/nginx/sites-available/jailbreaking /etc/nginx/sites-enabled/`
4. Test and reload: `nginx -t && systemctl reload nginx`

### HTTPS Options

**Let's Encrypt (public server):**
```bash
certbot --nginx -d yourdomain.com
```

**Self-signed cert (conference/LAN):**
```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/jailbreaking.key \
  -out /etc/ssl/certs/jailbreaking.crt \
  -subj "/CN=jailbreaking-challenge"
```

## Environment Variables

| Variable | Description |
|---|---|
| `MANAGER_MODE` | Default mode for `manager.py start` (`external` or `vllm`) |
| `CHAT_EINFRA_URL` | Base URL of the configured OpenAI-compatible API |
| `CHAT_EINFRA_KEY` | Optional API key for the configured API |
| `APP_PASSWORD` | Shared password for all attendees |
| `JWT_SECRET` | Secret for signing JWTs; if unset, the backend generates one at startup |
| `MODEL_NAME` | Model name passed to the configured API |
| `DB_PATH` | Path to SQLite database file |

In Slurm-managed mode, `manager.py` injects `CHAT_EINFRA_URL`, `CHAT_EINFRA_KEY`, `APP_PASSWORD`, `JWT_SECRET`, `MODEL_NAME`, and `DB_PATH` into the app job automatically.

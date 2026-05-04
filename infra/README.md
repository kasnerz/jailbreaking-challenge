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

1. Manual mode: run the backend yourself and point it at an external vLLM.
2. Slurm-managed mode: use `manager.py` to launch a split vLLM job and app job on the cluster.

## Slurm-Managed Deployment

This is the current cluster workflow.

From the project root:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python manager.py start \
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

## Manual Backend + External vLLM

```bash
# From project root
cp .env.example .env
# Edit .env with your values, then:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./infra/start.sh
```

In this mode, `infra/start.sh` starts only the FastAPI backend on `127.0.0.1:8000`.

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

Set `VLLM_BASE_URL=http://localhost:8001/v1` in `.env`.

You can also point `.env` at any other OpenAI-compatible vLLM endpoint instead of using the tunnel script.

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
| `VLLM_BASE_URL` | Base URL of the vLLM OpenAI-compatible API |
| `VLLM_API_KEY` | Optional API key for external vLLM services |
| `APP_PASSWORD` | Shared password for all attendees |
| `JWT_SECRET` | Secret for signing JWTs; if unset, the backend generates one at startup |
| `MODEL_NAME` | Model name passed to vLLM |
| `DB_PATH` | Path to SQLite database file |

In Slurm-managed mode, `manager.py` injects `VLLM_BASE_URL`, `APP_PASSWORD`, `JWT_SECRET`, `MODEL_NAME`, and `DB_PATH` into the app job automatically.

# Infrastructure Notes

## Architecture

```
[Attendees] ──HTTPS──► [Nginx (TLS + static files)]
                                 │
                          [FastAPI / uvicorn :8000]
                                 │
                          SQLite (attempts/stats)
                                 │
                    vLLM OpenAI-compat API
                   (GPU node :8000, reached
                    via SSH tunnel on :8001)
```

## Starting the Backend

```bash
# From project root
cp .env.example .env
# Edit .env with your values, then:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./infra/start.sh
```

## Starting vLLM on the GPU Node

SSH into the GPU node and run:

```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --max-model-len 4096 \
  --dtype auto \
  --disable-log-requests
```

Then, on the web server, open the SSH tunnel so the backend can reach vLLM:

```bash
./infra/tunnel.sh user@gpunode
```

Set `VLLM_BASE_URL=http://localhost:8001/v1` in `.env`.

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
| `APP_PASSWORD` | Shared password for all attendees |
| `JWT_SECRET` | Random secret for signing JWTs (generate with `openssl rand -hex 32`) |
| `MODEL_NAME` | Model name passed to vLLM |
| `DB_PATH` | Path to SQLite database file |

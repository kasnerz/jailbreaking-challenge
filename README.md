# Jailbreaking Challenge

This project is a small web app for running a prompt-injection and jailbreak challenge against an LLM.

Users log in with a shared password, pick a difficulty level, chat with the model, and try to get it to reveal a secret word. The backend records anonymous attempt statistics, and the frontend shows a simple chat interface plus a stats page.

## Stack

- Backend: FastAPI + SQLite
- Frontend: Astro + React
- Model API: any OpenAI-compatible endpoint, including vLLM
- Deployment helper: `manager.py`

## Project Layout

- `backend/`: FastAPI API, auth, database, level loading, LLM client
- `frontend/`: Astro app and React components
- `config/`: level definitions and secret words
- `infra/`: nginx notes and helper scripts
- `scripts/`: generated or checked-in launcher scripts

## Requirements

- Python 3.10+
- Node.js and npm
- An OpenAI-compatible API endpoint

Optional for cluster mode:

- Slurm
- vLLM-capable GPU environment

## Configuration

Copy the example environment file and update it for your setup:

```bash
cp .env.example .env
```

Important variables:

- `CHAT_EINFRA_URL`: base URL for the OpenAI-compatible API, for example `https://llm.ai.e-infra.cz/v1`
- `CHAT_EINFRA_KEY`: API key if the endpoint requires one
- `MODEL_NAME`: model name exposed by that API
- `APP_PASSWORD`: shared password used on the login page
- `JWT_SECRET`: secret used to sign auth tokens
- `DB_PATH`: SQLite database path

Level prompts live in `config/levels.yaml`.
Secret words live in `config/secrets.yaml`.

## Install Dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
cd ..
```

## How to run the app

### Option 1: Simple local run

This builds the frontend and starts the FastAPI app on `http://127.0.0.1:8000`.

```bash
./infra/start.sh
```

Use this when your `.env` already points at a working OpenAI-compatible API.

### Option 2: Local app with `manager.py` and an external API

This is the main managed workflow when the model endpoint already exists somewhere else.

```bash
python manager.py start \
  --mode external \
  --port 8000 \
  --password changeme \
  --model mini
```

Useful commands:

```bash
python manager.py status
python manager.py logs --target app
python manager.py restart-app
python manager.py stop
```

### Option 3: Slurm-managed vLLM mode

This launches a vLLM job and an app job through Slurm.

```bash
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
python manager.py logs --target app
python manager.py logs --target vllm
python manager.py restart-app
python manager.py stop
```

## How it works

1. Open the app in a browser.
2. Log in with the shared password.
3. Pick a level.
4. Chat with the model and try to get it to reveal the secret word.
5. View aggregate results on the stats page.

## Notes

- The backend checks health against the configured API by calling the models endpoint.
- The frontend is built before the backend starts.
- The SQLite database stores anonymous attempt and conversation data.
- The root app serves the built frontend from `frontend/dist`.

## More deployment details

See `infra/README.md` for nginx setup, HTTPS notes, and cluster deployment details.
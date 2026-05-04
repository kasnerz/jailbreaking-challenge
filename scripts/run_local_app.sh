#!/bin/bash
set -euo pipefail

echo "Building frontend..."
cd /lnet/work/people/kasner/projects/jailbreaking/frontend
npm install
export BASE_PATH="/nlg/jailbreaking"
npm run build

echo "Starting backend..."
cd /lnet/work/people/kasner/projects/jailbreaking

if [[ -f /lnet/work/people/kasner/projects/jailbreaking/venv/bin/activate ]]; then
    source /lnet/work/people/kasner/projects/jailbreaking/venv/bin/activate
fi

echo "*** Local App Setup Info ***"
echo "HOST: 127.0.0.1"
echo "PORT: 8642"
echo "MODEL: mini"
echo "LLM: https://llm.ai.e-infra.cz/v1"
echo "LOG: /lnet/work/people/kasner/projects/jailbreaking/logs/app_local.out"
echo "****************************"

export CHAT_EINFRA_URL="https://llm.ai.e-infra.cz/v1"
export CHAT_EINFRA_KEY="sk-1bb5ba06e5b94b84bf96f15ab8935af9"
export APP_PASSWORD="hackmeifyoucan"
export JWT_SECRET="sZFPVOo2WpXl03GdR2C0dGbQgFIZSibj"
export MODEL_NAME="mini"
export DB_PATH="/lnet/work/people/kasner/projects/jailbreaking/jailbreaking.db"

uvicorn backend.main:app --host 127.0.0.1 --port 8642 --root-path "/nlg/jailbreaking" --log-level info

#!/bin/bash
#SBATCH -J jailbreak_app
#SBATCH -p gpu-troja,gpu-ms,gpu-amd
#SBATCH -x tdll-8gpu5
#SBATCH -w dll-4gpu5
#SBATCH --mem=8G
#SBATCH -o /lnet/work/people/kasner/projects/jailbreaking/logs/app_%j.out
#SBATCH -e /lnet/work/people/kasner/projects/jailbreaking/logs/app_%j.out
#SBATCH --time=7-00:00:00

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

echo "*** App Setup Info ***"
echo "NODE: $(hostname)"
echo "PORT: 8642"
echo "MODEL: google/gemma-4-E4B-it"
echo "LLM: http://127.0.0.1:8777/v1"
echo "**********************"

export CHAT_EINFRA_URL="http://127.0.0.1:8777/v1"
export CHAT_EINFRA_KEY=""
export APP_PASSWORD="hackmeifyoucan"
export JWT_SECRET="x1JfjZHeVMvPF7dazpVcbRTVgofGEhje"
export MODEL_NAME="google/gemma-4-E4B-it"
export DB_PATH="/lnet/work/people/kasner/projects/jailbreaking/jailbreaking.db"

uvicorn backend.main:app --host 0.0.0.0 --port 8642 --root-path "/nlg/jailbreaking" --reload --log-level info

#!/bin/bash
#SBATCH -J jailbreak_app
#SBATCH -p gpu-troja
#SBATCH --constraint=gpuram40G
#SBATCH -G 1
#SBATCH -o /lnet/work/people/kasner/projects/jailbreaking/logs/app_%j.out
#SBATCH -e /lnet/work/people/kasner/projects/jailbreaking/logs/app_%j.out
#SBATCH --time=7-00:00:00

echo "Building frontend..."
cd /lnet/work/people/kasner/projects/jailbreaking/frontend
npm install
npm run build

echo "Starting backend and vLLM..."
cd /lnet/work/people/kasner/projects/jailbreaking

if [[ -f /lnet/work/people/kasner/projects/jailbreaking/venv/bin/activate ]]; then
    source /lnet/work/people/kasner/projects/jailbreaking/venv/bin/activate
fi

echo "*** Node Setup Info ***"
echo "NODE: $(hostname)"
echo "PORT: 8642"
echo "MODEL: google/gemma-4-E4B-it"
echo "***********************"

VLLM_PORT=$(python -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()')

python -m vllm.entrypoints.openai.api_server \
    --model google/gemma-4-E4B-it \
    --served-model-name default \
    --port $VLLM_PORT \
    --host 127.0.0.1 \
    --api-key none &
VLLM_PID=$!

echo "Waiting for vLLM to be ready on port $VLLM_PORT..."
for i in {1..60}; do
    if curl -s http://127.0.0.1:$VLLM_PORT/health > /dev/null; then
        echo "vLLM is ready!"
        break
    fi
    sleep 5
done

export VLLM_BASE_URL="http://127.0.0.1:$VLLM_PORT/v1"
export APP_PASSWORD="hackmeifyoucan"
export JWT_SECRET="sqQ8nfo0GJnfTXRYt0Y4pnaHFHWMZqni"
export MODEL_NAME="google/gemma-4-E4B-it"
export DB_PATH="/lnet/work/people/kasner/projects/jailbreaking/jailbreaking.db"

uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8642 \
    --workers 2 \
    --log-level info

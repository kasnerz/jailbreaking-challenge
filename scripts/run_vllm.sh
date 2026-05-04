#!/bin/bash
#SBATCH -J jailbreak_vllm
#SBATCH -p gpu-troja,gpu-ms,gpu-amd
#SBATCH -x tdll-8gpu5
#SBATCH --constraint=gpuram64G
#SBATCH -G 1
#SBATCH --mem=32G
#SBATCH -o /lnet/work/people/kasner/projects/jailbreaking/logs/vllm_%j.out
#SBATCH -e /lnet/work/people/kasner/projects/jailbreaking/logs/vllm_%j.out
#SBATCH --time=7-00:00:00

set -euo pipefail

cd /lnet/work/people/kasner/projects/jailbreaking

echo "*** vLLM Setup Info ***"
echo "NODE: $(hostname)"
echo "MODEL: google/gemma-4-E4B-it"
echo "PORT: 8777"
echo "***********************"

if [[ -f /lnet/work/people/kasner/virtualenv/vllm-amd/bin/activate ]]; then
    source /lnet/work/people/kasner/virtualenv/vllm-amd/bin/activate
fi

vllm serve google/gemma-4-E4B-it     --port 8777     --host 127.0.0.1     --api-key none

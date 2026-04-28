import argparse
import json
import os
import secrets
import string
import subprocess

STATE_FILE = "state.json"
LOG_DIR = "logs"
SCRIPT_DIR = "scripts"


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def start_job(port, password, model_id, gpus, gpuram):
    state = load_json(STATE_FILE)
    if "job" in state:
        print("Job already running. Currently tracked job ID:", state["job"]["job_id"])
        return

    jwt_secret = "".join(
        secrets.choice(string.ascii_letters + string.digits) for i in range(32)
    )

    slurm_script_path = os.path.join(SCRIPT_DIR, "run_app.sh")
    log_path = os.path.join(LOG_DIR, "app_%j.out")

    project_dir = os.path.abspath(os.path.dirname(__file__))
    venv_path = os.path.join(project_dir, "venv")
    if not os.path.exists(venv_path):
        venv_path = os.path.join(project_dir, ".venv")

    # If the user wants to ensure the frontend is built, doing it before vLLM loading
    script_content = f"""#!/bin/bash
#SBATCH -J jailbreak_app
#SBATCH -p gpu-troja
#SBATCH --constraint=gpuram{gpuram}
#SBATCH -G {gpus}
#SBATCH -o {os.path.abspath(log_path)}
#SBATCH -e {os.path.abspath(log_path)}
#SBATCH --time=7-00:00:00

echo "Building frontend..."
cd {project_dir}/frontend
npm install
npm run build

echo "Starting backend and vLLM..."
cd {project_dir}

if [[ -f {venv_path}/bin/activate ]]; then
    source {venv_path}/bin/activate
fi

echo "*** Node Setup Info ***"
echo "NODE: $(hostname)"
echo "PORT: {port}"
echo "MODEL: {model_id}"
echo "***********************"

VLLM_PORT=8777
VLLM_VENV="/lnet/work/people/kasner/virtualenv/vllm"

if [[ -f $VLLM_VENV/bin/activate ]]; then
    source $VLLM_VENV/bin/activate
fi

python -m vllm.entrypoints.openai.api_server \\
    --model {model_id} \\
    --served-model-name default \\
    --port $VLLM_PORT \\
    --host 127.0.0.1 \\
    --api-key none &
VLLM_PID=$!

echo "Waiting for vLLM to be ready on port $VLLM_PORT..."
for i in {{1..60}}; do
    if curl -s http://127.0.0.1:$VLLM_PORT/health > /dev/null; then
        echo "vLLM is ready!"
        break
    fi
    sleep 5
done

# Switch back to the project venv for the backend
if [[ -f {venv_path}/bin/activate ]]; then
    source {venv_path}/bin/activate
fi

export VLLM_BASE_URL="http://127.0.0.1:$VLLM_PORT/v1"
export APP_PASSWORD="{password}"
export JWT_SECRET="{jwt_secret}"
export MODEL_NAME="{model_id}"
export DB_PATH="{project_dir}/jailbreaking.db"

uvicorn backend.main:app \\
    --host 0.0.0.0 \\
    --port {port} \\
    --reload \
    --log-level info
"""
    with open(slurm_script_path, "w") as f:
        f.write(script_content)

    print(f"Submitting job with Model: {model_id}, Port: {port}, GPUs: {gpus}")
    result = subprocess.run(
        ["sbatch", slurm_script_path], capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Failed to submit: {result.stderr}")
        return

    output = result.stdout.strip()
    print(output)
    job_id = output.split()[-1]

    state["job"] = {
        "job_id": job_id,
        "port": port,
        "log_path": os.path.abspath(log_path.replace("%j", job_id)),
        "model_id": model_id,
        "password": password,
    }
    save_json(STATE_FILE, state)


def stop_job():
    state = load_json(STATE_FILE)
    if "job" not in state:
        print("No job is currently tracked.")
        return

    job_id = state["job"]["job_id"]
    print(f"Canceling job {job_id}...")
    subprocess.run(["scancel", str(job_id)])

    del state["job"]
    save_json(STATE_FILE, state)
    print("Stopped.")


def status():
    state = load_json(STATE_FILE)
    if "job" not in state:
        print("No job is currently running.")
        return

    job_id = state["job"]["job_id"]
    port = state["job"]["port"]
    log_file = state["job"]["log_path"]
    model_id = state["job"]["model_id"]
    password = state["job"]["password"]

    result = subprocess.run(
        ["squeue", "-j", str(job_id), "-O", "State,NodeList", "-h"],
        capture_output=True,
        text=True,
    )

    parts = result.stdout.strip().split()
    if len(parts) >= 2:
        s_state = parts[0]
        node = parts[1]
    elif len(parts) == 1:
        s_state = parts[0]
        node = "N/A"
    else:
        s_state = "STOPPED/UNKNOWN"
        node = "N/A"

    print(f"Job ID   : {job_id}")
    print(f"Status   : {s_state}")
    print(f"Node     : {node}")
    print(f"Port     : {port}")
    print(f"Password : {password}")
    print(f"Model ID : {model_id}")
    print(f"Log File : {log_file}")

    if node != "N/A" and s_state == "RUNNING":
        print(f"\nTo access locally, set up SSH port forwarding:")
        print(f"ssh -NL {port}:localhost:{port} user@{node}")


def show_logs():
    state = load_json(STATE_FILE)
    if "job" not in state:
        print("No job is currently tracked.")
        return
    log_path = state["job"]["log_path"]
    if os.path.exists(log_path):
        print(f"--- Top of log ({log_path}) ---")
        subprocess.run(["head", "-n", "10", log_path])
        print("\n--- Tailing real-time logs ---")
        subprocess.run(["tail", "-n", "50", "-f", log_path])
    else:
        print(f"Log file not found yet: {log_path}")


def main():
    parser = argparse.ArgumentParser(description="Manage Jailbreaking app on Slurm")
    subparsers = parser.add_subparsers(dest="command")

    start_p = subparsers.add_parser("start", help="Start the app")
    start_p.add_argument(
        "--port", type=int, default=8642, help="Port to expose the app on"
    )
    start_p.add_argument("--password", required=True, help="App password")
    start_p.add_argument("--model", required=True, help="HuggingFace model ID")
    start_p.add_argument("--gpus", type=int, default=1, help="Number of GPUs")
    start_p.add_argument(
        "--gpuram", default="24G", help="GPU RAM required (e.g. 24G, 40G, 80G)"
    )

    subparsers.add_parser("stop", help="Stop the app")
    subparsers.add_parser("status", help="Show status")
    subparsers.add_parser("logs", help="Tail logs")

    args = parser.parse_args()

    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(SCRIPT_DIR, exist_ok=True)

    if args.command == "start":
        start_job(args.port, args.password, args.model, args.gpus, args.gpuram)
    elif args.command == "stop":
        stop_job()
    elif args.command == "status":
        status()
    elif args.command == "logs":
        show_logs()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

import argparse
import json
import os
import secrets
import signal
import string
import subprocess
import time

from dotenv import dotenv_values

STATE_FILE = "state.json"
LOG_DIR = "logs"
SCRIPT_DIR = "scripts"
VLLM_PORT = 8777
VLLM_VENV = "/lnet/work/people/kasner/virtualenv/vllm-amd"
GPU_PARTITIONS = "gpu-troja,gpu-ms,gpu-amd"
JOB_NODE_WAIT_SECONDS = 120
JOB_NODE_POLL_SECONDS = 5


def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    return dotenv_values(env_path)


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def generate_jwt_secret():
    return "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(32)
    )


def get_project_dir():
    return os.path.abspath(os.path.dirname(__file__))


def get_project_venv_path(project_dir):
    venv_path = os.path.join(project_dir, "venv")
    if not os.path.exists(venv_path):
        venv_path = os.path.join(project_dir, ".venv")
    return venv_path


def run_command(command):
    return subprocess.run(command, capture_output=True, text=True)


def is_local_process_active(pid):
    if not pid:
        return False

    try:
        os.kill(pid, 0)
    except OSError:
        return False

    return True


def get_job_status(job_id):
    result = run_command(["squeue", "-j", str(job_id), "-O", "State,NodeList", "-h"])
    parts = result.stdout.strip().split()

    if len(parts) >= 2:
        return {"state": parts[0], "node": parts[1]}
    if len(parts) == 1:
        return {"state": parts[0], "node": "N/A"}
    return {"state": "STOPPED/UNKNOWN", "node": "N/A"}


def is_job_active(job_info):
    return job_info["state"] not in {"STOPPED/UNKNOWN", "COMPLETED", "CANCELLED"}


def wait_for_job_node(job_id, timeout_seconds=JOB_NODE_WAIT_SECONDS):
    deadline = time.time() + timeout_seconds
    last_info = None

    while time.time() < deadline:
        last_info = get_job_status(job_id)
        node = last_info["node"]
        if node not in {"N/A", "(null)"}:
            return node
        time.sleep(JOB_NODE_POLL_SECONDS)

    return last_info["node"] if last_info else "N/A"


def ensure_split_state(state):
    state.setdefault("config", {})
    return state


def sync_split_state(state):
    for key in ["vllm", "app"]:
        job = state.get(key)
        if not job:
            continue

        if job.get("kind") == "local":
            if is_local_process_active(job.get("pid")):
                job["state"] = "RUNNING"
                job["node"] = "local"
            else:
                del state[key]
            continue

        job_info = get_job_status(job["job_id"])
        job["state"] = job_info["state"]
        job["node"] = job_info["node"]

        if not is_job_active(job_info):
            del state[key]

    return state


def build_vllm_script(project_dir, model_id, gpus, gpuram, mem, log_path):
    return f"""#!/bin/bash
#SBATCH -J jailbreak_vllm
#SBATCH -p {GPU_PARTITIONS}
#SBATCH -x tdll-8gpu5
#SBATCH --constraint=gpuram{gpuram}
#SBATCH -G {gpus}
#SBATCH --mem={mem}
#SBATCH -o {os.path.abspath(log_path)}
#SBATCH -e {os.path.abspath(log_path)}
#SBATCH --time=7-00:00:00

set -euo pipefail

cd {project_dir}

echo "*** vLLM Setup Info ***"
echo "NODE: $(hostname)"
echo "MODEL: {model_id}"
echo "PORT: {VLLM_PORT}"
echo "***********************"

if [[ -f {VLLM_VENV}/bin/activate ]]; then
    source {VLLM_VENV}/bin/activate
fi

vllm serve {model_id} \
    --port {VLLM_PORT} \
    --host 127.0.0.1 \
    --api-key none
"""


def build_app_script(
    project_dir,
    venv_path,
    port,
    password,
    model_id,
    base_path,
    jwt_secret,
    app_mem,
    log_path,
    node,
    llm_url,
    llm_api_key,
):
    return f"""#!/bin/bash
#SBATCH -J jailbreak_app
#SBATCH -p {GPU_PARTITIONS}
#SBATCH -x tdll-8gpu5
#SBATCH -w {node}
#SBATCH --mem={app_mem}
#SBATCH -o {os.path.abspath(log_path)}
#SBATCH -e {os.path.abspath(log_path)}
#SBATCH --time=7-00:00:00

set -euo pipefail

echo "Building frontend..."
cd {project_dir}/frontend
npm install
export BASE_PATH="{base_path}"
npm run build

echo "Starting backend..."
cd {project_dir}

if [[ -f {venv_path}/bin/activate ]]; then
    source {venv_path}/bin/activate
fi

echo "*** App Setup Info ***"
echo "NODE: $(hostname)"
echo "PORT: {port}"
echo "MODEL: {model_id}"
echo "LLM: {llm_url}"
echo "**********************"

export CHAT_EINFRA_URL="{llm_url}"
export CHAT_EINFRA_KEY="{llm_api_key}"
export APP_PASSWORD="{password}"
export JWT_SECRET="{jwt_secret}"
export MODEL_NAME="{model_id}"
export DB_PATH="{project_dir}/jailbreaking.db"

uvicorn backend.main:app --host 0.0.0.0 --port {port} --root-path "{base_path}" --reload --log-level info
"""


def build_local_app_script(
    project_dir,
    venv_path,
    port,
    password,
    model_id,
    base_path,
    jwt_secret,
    log_path,
    llm_url,
    llm_api_key,
):
    return f"""#!/bin/bash
set -euo pipefail

echo "Building frontend..."
cd {project_dir}/frontend
npm install
export BASE_PATH="{base_path}"
npm run build

echo "Starting backend..."
cd {project_dir}

if [[ -f {venv_path}/bin/activate ]]; then
    source {venv_path}/bin/activate
fi

echo "*** Local App Setup Info ***"
echo "HOST: 127.0.0.1"
echo "PORT: {port}"
echo "MODEL: {model_id}"
echo "LLM: {llm_url}"
echo "LOG: {os.path.abspath(log_path)}"
echo "****************************"

export CHAT_EINFRA_URL="{llm_url}"
export CHAT_EINFRA_KEY="{llm_api_key}"
export APP_PASSWORD="{password}"
export JWT_SECRET="{jwt_secret}"
export MODEL_NAME="{model_id}"
export DB_PATH="{project_dir}/jailbreaking.db"

uvicorn backend.main:app --host 127.0.0.1 --port {port} --root-path "{base_path}" --log-level info
"""


def write_script(script_name, script_content):
    script_path = os.path.join(SCRIPT_DIR, script_name)
    with open(script_path, "w") as f:
        f.write(script_content)
    return script_path


def write_and_submit_script(script_name, script_content):
    script_path = write_script(script_name, script_content)

    result = run_command(["sbatch", script_path])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Failed to submit Slurm job")

    output = result.stdout.strip()
    print(output)
    return output.split()[-1]


def start_vllm_job(state, model_id, gpus, gpuram, mem):
    project_dir = get_project_dir()
    log_path = os.path.join(LOG_DIR, "vllm_%j.out")
    script_content = build_vllm_script(
        project_dir, model_id, gpus, gpuram, mem, log_path
    )

    print(f"Submitting vLLM job with Model: {model_id}, GPUs: {gpus}")
    job_id = write_and_submit_script("run_vllm.sh", script_content)
    node = wait_for_job_node(job_id)

    state["vllm"] = {
        "job_id": job_id,
        "port": VLLM_PORT,
        "log_path": os.path.abspath(log_path.replace("%j", job_id)),
        "model_id": model_id,
        "node": node,
        "state": get_job_status(job_id)["state"],
    }
    return state


def start_app_job(state):
    config = state["config"]
    vllm = state.get("vllm")
    if not vllm:
        raise RuntimeError("vLLM job is not tracked. Start vLLM first.")

    node = get_job_status(vllm["job_id"])["node"]
    if node == "N/A":
        node = vllm.get("node", "N/A")
    if node == "N/A":
        raise RuntimeError("vLLM job does not have an allocated node yet.")

    project_dir = get_project_dir()
    venv_path = get_project_venv_path(project_dir)
    log_path = os.path.join(LOG_DIR, "app_%j.out")
    script_content = build_app_script(
        project_dir=project_dir,
        venv_path=venv_path,
        port=config["port"],
        password=config["password"],
        model_id=config["model_id"],
        base_path=config["base_path"],
        jwt_secret=config["jwt_secret"],
        app_mem=config["app_mem"],
        log_path=log_path,
        node=node,
        llm_url=f"http://127.0.0.1:{VLLM_PORT}/v1",
        llm_api_key="",
    )

    print(f"Submitting app job on node {node} at port {config['port']}")
    job_id = write_and_submit_script("run_app.sh", script_content)
    app_info = get_job_status(job_id)

    state["app"] = {
        "kind": "slurm",
        "job_id": job_id,
        "port": config["port"],
        "log_path": os.path.abspath(log_path.replace("%j", job_id)),
        "password": config["password"],
        "node": app_info["node"] if app_info["node"] != "N/A" else node,
        "state": app_info["state"],
    }
    state["vllm"]["node"] = node
    return state


def start_local_app(state, llm_url, llm_api_key):
    config = state["config"]
    project_dir = get_project_dir()
    venv_path = get_project_venv_path(project_dir)
    log_path = os.path.join(LOG_DIR, "app_local.out")
    script_content = build_local_app_script(
        project_dir=project_dir,
        venv_path=venv_path,
        port=config["port"],
        password=config["password"],
        model_id=config["model_id"],
        base_path=config["base_path"],
        jwt_secret=config["jwt_secret"],
        log_path=log_path,
        llm_url=llm_url,
        llm_api_key=llm_api_key,
    )
    script_path = write_script("run_local_app.sh", script_content)

    with open(log_path, "w") as log_file:
        process = subprocess.Popen(
            ["bash", script_path],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    time.sleep(1)
    if process.poll() is not None:
        raise RuntimeError(
            f"Local app exited immediately. Check the log: {os.path.abspath(log_path)}"
        )

    state["app"] = {
        "kind": "local",
        "pid": process.pid,
        "port": config["port"],
        "log_path": os.path.abspath(log_path),
        "password": config["password"],
        "node": "local",
        "state": "RUNNING",
    }
    return state


def start_job(
    mode,
    port,
    password,
    model_id,
    gpus,
    gpuram,
    mem,
    app_mem,
    base_path,
    llm_url,
    llm_api_key,
):
    state = load_json(STATE_FILE)

    state = ensure_split_state(state)
    state = sync_split_state(state)

    active_mode = state.get("config", {}).get("mode")
    if active_mode and active_mode != mode and (state.get("vllm") or state.get("app")):
        print(
            "A different manager mode is already running. Stop tracked processes first."
        )
        return

    if not state["config"]:
        state["config"] = {
            "mode": mode,
            "port": port,
            "password": password,
            "model_id": model_id,
            "gpus": gpus,
            "gpuram": gpuram,
            "mem": mem,
            "app_mem": app_mem,
            "base_path": base_path,
            "jwt_secret": generate_jwt_secret(),
        }

    config = state["config"]

    if config.get("mode") != mode:
        print("Tracked config uses a different mode. Stop tracked processes first.")
        return

    if mode == "external":
        if state.get("app"):
            print("External app is already running.")
            return

        try:
            state = start_local_app(state, llm_url, llm_api_key)
        except RuntimeError as exc:
            print(str(exc))
            save_json(STATE_FILE, state)
            return

        save_json(STATE_FILE, state)
        return

    if state.get("vllm") and state.get("app"):
        print("vLLM and app jobs are already running.")
        return

    if state.get("vllm") and config["model_id"] != model_id:
        print(
            "vLLM is already running with a different tracked model. Stop both jobs to change models."
        )
        return

    try:
        if not state.get("vllm"):
            state = start_vllm_job(
                state,
                config["model_id"],
                config["gpus"],
                config["gpuram"],
                config["mem"],
            )

        if not state.get("app"):
            state = start_app_job(state)
    except RuntimeError as exc:
        print(str(exc))
        save_json(STATE_FILE, state)
        return

    save_json(STATE_FILE, state)


def stop_job():
    state = load_json(STATE_FILE)

    state = ensure_split_state(state)
    state = sync_split_state(state)

    if not state.get("vllm") and not state.get("app"):
        print("No jobs are currently tracked.")
        return

    if state.get("app"):
        if state["app"].get("kind") == "local":
            pid = state["app"]["pid"]
            print(f"Stopping local app process {pid}...")
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        else:
            job_id = state["app"]["job_id"]
            print(f"Canceling app job {job_id}...")
            subprocess.run(["scancel", str(job_id)])
        del state["app"]

    if state.get("vllm"):
        if state["vllm"].get("kind") == "local":
            pid = state["vllm"]["pid"]
            print(f"Stopping local vLLM process {pid}...")
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        else:
            job_id = state["vllm"]["job_id"]
            print(f"Canceling vLLM job {job_id}...")
            subprocess.run(["scancel", str(job_id)])
        del state["vllm"]

    if not state.get("vllm") and not state.get("app"):
        state.pop("config", None)

    save_json(STATE_FILE, state)
    print("Stopped.")


def restart_app():
    env = load_env()
    state = load_json(STATE_FILE)

    state = ensure_split_state(state)
    state = sync_split_state(state)

    if state.get("config", {}).get("mode") == "external":
        if state.get("app"):
            pid = state["app"].get("pid")
            if pid:
                print(f"Stopping local app process {pid}...")
                try:
                    os.killpg(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            del state["app"]

        llm_url = env.get("CHAT_EINFRA_URL") or env.get("VLLM_BASE_URL")
        llm_api_key = env.get("CHAT_EINFRA_KEY") or env.get("VLLM_API_KEY", "")

        try:
            state = start_local_app(state, llm_url, llm_api_key)
        except RuntimeError as exc:
            print(str(exc))
            save_json(STATE_FILE, state)
            return

        save_json(STATE_FILE, state)
        return

    if not state.get("vllm"):
        print("No tracked vLLM job found. Start the app first.")
        return

    vllm_info = get_job_status(state["vllm"]["job_id"])
    if not is_job_active(vllm_info):
        print("Tracked vLLM job is not running. Start again to recreate both jobs.")
        state.pop("vllm", None)
        state.pop("app", None)
        state.pop("config", None)
        save_json(STATE_FILE, state)
        return

    state["vllm"]["node"] = vllm_info["node"]
    state["vllm"]["state"] = vllm_info["state"]

    if state.get("app"):
        print(f"Canceling app job {state['app']['job_id']}...")
        subprocess.run(["scancel", str(state["app"]["job_id"])])
        del state["app"]

    try:
        state = start_app_job(state)
    except RuntimeError as exc:
        print(str(exc))
        save_json(STATE_FILE, state)
        return

    save_json(STATE_FILE, state)


def print_job_block(label, job):
    if not job:
        print(f"{label:<8}: not running")
        return

    identifier = job.get("job_id") or job.get("pid") or "unknown"
    print(f"{label:<8}: {identifier}")
    if job.get("kind"):
        print(f"Kind     : {job['kind']}")
    print(f"State    : {job.get('state', 'UNKNOWN')}")
    print(f"Node     : {job.get('node', 'N/A')}")
    if "pid" in job:
        print(f"PID      : {job['pid']}")
    if "port" in job:
        print(f"Port     : {job['port']}")
    if "password" in job:
        print(f"Password : {job['password']}")
    if "model_id" in job:
        print(f"Model ID : {job['model_id']}")
    print(f"Log File : {job['log_path']}")


def status():
    state = load_json(STATE_FILE)

    state = ensure_split_state(state)
    state = sync_split_state(state)
    save_json(STATE_FILE, state)

    if not state.get("vllm") and not state.get("app"):
        print("No jobs are currently running.")
        return

    if state.get("config", {}).get("mode"):
        print(f"Mode     : {state['config']['mode']}")
        print()

    if state.get("vllm"):
        print_job_block("vLLM", state["vllm"])
    else:
        print_job_block("vLLM", None)

    print()

    if state.get("app"):
        print_job_block("App", state["app"])
    else:
        print_job_block("App", None)

    if state.get("app") and state["app"].get("kind") == "local":
        port = state["app"]["port"]
        print(f"\nOpen locally: http://127.0.0.1:{port}")
    elif state.get("app") and state["app"].get("node") != "N/A":
        port = state["app"]["port"]
        node = state["app"]["node"]
        print("\nTo access locally, set up SSH port forwarding:")
        print(f"ssh -NL {port}:localhost:{port} user@{node}")


def show_logs(target):
    state = load_json(STATE_FILE)

    state = ensure_split_state(state)
    job = state.get(target)
    if not job:
        print(f"No {target} job is currently tracked.")
        return
    log_path = job["log_path"]

    if os.path.exists(log_path):
        print(f"--- Top of log ({log_path}) ---")
        subprocess.run(["head", "-n", "10", log_path])
        print("\n--- Tailing real-time logs ---")
        subprocess.run(["tail", "-n", "50", "-f", log_path])
    else:
        print(f"Log file not found yet: {log_path}")


def main():
    env = load_env()

    parser = argparse.ArgumentParser(
        description="Manage Jailbreaking app locally or on Slurm"
    )
    subparsers = parser.add_subparsers(dest="command")

    start_p = subparsers.add_parser(
        "start", help="Start the app in external or vLLM mode"
    )
    start_p.add_argument(
        "--mode",
        choices=["external", "vllm"],
        default=env.get("MANAGER_MODE", "external"),
        help="Manager mode: external runs locally against an existing OpenAI-compatible API; vllm submits split Slurm jobs.",
    )
    start_p.add_argument(
        "--port", type=int, default=8642, help="Port to expose the app on"
    )
    start_p.add_argument(
        "--password",
        default=env.get("APP_PASSWORD"),
        required=not env.get("APP_PASSWORD"),
        help="App password (or set APP_PASSWORD in .env)",
    )
    start_p.add_argument(
        "--model",
        default=env.get("MODEL_NAME"),
        required=not env.get("MODEL_NAME"),
        help="Model ID or alias for the configured API (or set MODEL_NAME in .env)",
    )
    start_p.add_argument("--gpus", type=int, default=1, help="Number of GPUs")
    start_p.add_argument(
        "--gpuram",
        default=env.get("GPURAM", "24G"),
        help="GPU RAM required (e.g. 24G, 40G, 80G) (or set GPURAM in .env)",
    )
    start_p.add_argument(
        "--base-path",
        default=env.get("BASE_PATH", ""),
        help="Base path for reverse proxy (e.g. /nlg/jailbreaking) (or set BASE_PATH in .env)",
    )
    start_p.add_argument(
        "--mem", default=env.get("VLLM_MEM", "32G"), help="CPU RAM for the vLLM job"
    )
    start_p.add_argument(
        "--app-mem", default=env.get("APP_MEM", "8G"), help="CPU RAM for the app job"
    )

    subparsers.add_parser("restart-app", help="Restart only the frontend/backend job")
    subparsers.add_parser("stop", help="Stop all tracked jobs")
    subparsers.add_parser("status", help="Show status")

    logs_p = subparsers.add_parser("logs", help="Tail logs")
    logs_p.add_argument(
        "--target",
        choices=["app", "vllm"],
        default="app",
        help="Which split-job log to tail",
    )

    args = parser.parse_args()

    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(SCRIPT_DIR, exist_ok=True)

    if args.command == "start":
        llm_url = env.get("CHAT_EINFRA_URL") or env.get("VLLM_BASE_URL")
        llm_api_key = env.get("CHAT_EINFRA_KEY") or env.get("VLLM_API_KEY", "")
        start_job(
            args.mode,
            args.port,
            args.password,
            args.model,
            args.gpus,
            args.gpuram,
            args.mem,
            args.app_mem,
            args.base_path,
            llm_url,
            llm_api_key,
        )
    elif args.command == "restart-app":
        restart_app()
    elif args.command == "stop":
        stop_job()
    elif args.command == "status":
        status()
    elif args.command == "logs":
        show_logs(args.target)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

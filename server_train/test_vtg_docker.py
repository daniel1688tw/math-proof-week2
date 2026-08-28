# -*- coding: utf-8 -*-
"""Verify the isolated one-GPU Docker contract for remote VTG evaluation."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
COMPOSE = HERE / "docker-compose.vtg-eval.yml"
RUNNER = HERE / "run_vtg_eval.sh"


def main() -> None:
    env = os.environ.copy()
    env.update({
        "VTG_PROJECT_DIR": "/srv/daniel-vtg/project",
        "VTG_BASE_MODEL_DIR": "/srv/daniel-vtg/base",
        "VTG_ADAPTER_DIR": "/srv/daniel-vtg/adapter",
        "VTG_GGUF_DIR": "/srv/daniel-vtg/gguf",
        "VTG_OLLAMA_MODELS_DIR": "/srv/daniel-vtg/ollama-models",
        "VTG_GPU_ID": "1",
    })
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "config", "--format", "json"],
        cwd=HERE, env=env, text=True, encoding="utf-8", errors="replace",
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)
    service = config["services"]["daniel-vtg-eval"]

    assert service["container_name"] == "daniel-vtg-eval"
    assert service["image"] == "daniel-qlora-train:latest"
    assert service["network_mode"] == "none"
    assert "ports" not in service
    assert service["command"] == ["bash", "/workspace/server_train/run_vtg_eval.sh"]
    assert service["environment"]["FINAL_ADAPTER"] == "qlora_adapter_v9"
    assert service["environment"]["REVIEW_MODEL"] == "qwen3-4b-thinking-2507:latest"
    assert service["environment"]["OLLAMA_URL"] == "http://127.0.0.1:11434/api/chat"
    assert service["environment"]["VERIFY_THEN_GENERATE"] == "1"
    assert service["environment"]["REVIEW_BACKSTOP"] == "1"

    devices = service["deploy"]["resources"]["reservations"]["devices"]
    assert devices == [{"capabilities": ["gpu"], "device_ids": ["1"], "driver": "nvidia"}]
    volumes = {item["target"]: item for item in service["volumes"]}
    assert volumes["/workspace/learn_path/socratic_tutor/qwen3_4b"]["read_only"] is True
    assert volumes["/workspace/dataset/qlora_adapter_v9"]["read_only"] is True
    assert volumes["/assets"]["read_only"] is True
    assert volumes["/usr/local/bin/ollama"]["read_only"] is True

    bash = shutil.which("bash")
    assert bash, "bash is required to validate the Linux runner"
    syntax = subprocess.run(
        [bash, "-n", RUNNER.name], cwd=HERE, text=True, encoding="utf-8",
        errors="replace", capture_output=True,
    )
    assert syntax.returncode == 0, syntax.stderr
    print("PASS: isolated VTG Docker contract")


if __name__ == "__main__":
    main()

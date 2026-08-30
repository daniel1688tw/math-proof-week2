# -*- coding: utf-8 -*-
"""Static safety contract for the lab 4090 dialogue simulation runner."""
from pathlib import Path
import os
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent


def test_runner_is_isolated_to_own_container_and_gpu1():
    text = (HERE / "run_limit_levels_remote.sh").read_text(encoding="utf-8")

    assert "daniel-limit-levels-sim" in text
    assert "--gpus" in text and "device=1" in text
    assert "127.0.0.1:8899:8899" in text
    assert "127.0.0.1:11435:11434" in text
    assert "-e QUANT=4bit" in text
    assert "run_limit_levels_service.sh" in text
    assert "/usr/local/bin/ollama" in text
    assert "nvidia-smi --id=1" in text
    assert "docker system prune" not in text
    assert "--gpus all" not in text
    assert "docker rm -f" not in text


def test_runner_exposes_start_status_and_stop_actions():
    text = (HERE / "run_limit_levels_remote.sh").read_text(encoding="utf-8")

    for action in ("start)", "status)", "stop)"):
        assert action in text
    assert "===READY===" in text
    assert "===STOPPED===" in text


def test_start_timeout_stops_only_the_owned_container():
    runner = HERE / "run_limit_levels_remote.sh"
    with tempfile.TemporaryDirectory() as tmp:
        fake_bin = Path(tmp)
        marker = fake_bin / "docker_calls.txt"
        marker.write_text("", encoding="utf-8")
        (fake_bin / "nvidia-smi").write_text(
            "#!/usr/bin/env bash\n"
            "case \"$*\" in\n"
            "  *memory.used*utilization.gpu*) echo '1, 0' ;;\n"
            "  *memory.used*) echo '1' ;;\n"
            "  *utilization.gpu*) echo '0' ;;\n"
            "  *) echo '1, 24080, 0 %' ;;\n"
            "esac\n", encoding="utf-8")
        (fake_bin / "docker").write_text(
            "#!/usr/bin/env bash\n"
            f"printf '%s\\n' \"$*\" >> '{marker.as_posix()}'\n"
            "case \"$1\" in\n"
            "  run) echo fake-container-id ;;\n"
            f"  ps) grep -q '^run ' '{marker.as_posix()}' && "
            "echo daniel-limit-levels-sim || true ;;\n"
            "  logs) exit 0 ;;\n"
            "  stop) exit 0 ;;\n"
            "esac\n", encoding="utf-8")
        (fake_bin / "sleep").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        for executable in ("nvidia-smi", "docker", "sleep"):
            os.chmod(fake_bin / executable, 0o755)
        env = dict(os.environ)
        env["PATH"] = f"{fake_bin.as_posix()}:/usr/bin:/bin"
        env["LIMIT_LEVELS_READY_ATTEMPTS"] = "2"
        env["LIMIT_LEVELS_READY_INTERVAL"] = "0"
        vtg_root = fake_bin / "vtg"
        (vtg_root / "gguf").mkdir(parents=True)
        (vtg_root / "ollama_models").mkdir()
        (vtg_root / "gguf" / "Qwen3-4B-Thinking-2507-Q4_K_M.gguf").write_bytes(b"stub")
        env["LIMIT_LEVELS_VTG_ROOT"] = vtg_root.as_posix()
        git_bash = Path(r"C:\Program Files\Git\bin\bash.exe")
        result = subprocess.run(
            [str(git_bash), runner.as_posix(), "start"], env=env,
            capture_output=True, text=True, encoding="utf-8", timeout=10)

        calls = marker.read_text(encoding="utf-8")
        assert result.returncode == 6, (
            f"returncode={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        assert "stop -t 20 daniel-limit-levels-sim" in calls
        assert "stop -t 20 " in calls


def test_evaluation_wrapper_stops_remote_container_when_evaluator_fails():
    wrapper = HERE / "run_limit_levels_evaluation.sh"
    with tempfile.TemporaryDirectory() as tmp:
        fake_bin = Path(tmp)
        ssh_calls = fake_bin / "ssh_calls.txt"
        ssh_calls.write_text("", encoding="utf-8")
        (fake_bin / "timeout").write_text(
            "#!/usr/bin/env bash\nshift\nexec \"$@\"\n", encoding="utf-8")
        (fake_bin / "ssh").write_text(
            "#!/usr/bin/env bash\n"
            f"printf '%s\\n' \"$*\" >> '{ssh_calls.as_posix()}'\n"
            "case \"$*\" in\n"
            "  *' stop'*) echo 'GPU1_AFTER=1 MiB, 24080 MiB, 0 %'; echo '===STOPPED===' ;;\n"
            "  *'mkdir -p'*) echo '===DIR_READY===' ;;\n"
            "  *'PREFLIGHT_DONE'*) echo '===PREFLIGHT_DONE===' ;;\n"
            "  *' start'*) echo '===READY===' ;;\n"
            "esac\n", encoding="utf-8")
        (fake_bin / "scp").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (fake_bin / "fake-python").write_text("#!/usr/bin/env bash\nexit 7\n", encoding="utf-8")
        for executable in ("timeout", "ssh", "scp", "fake-python"):
            os.chmod(fake_bin / executable, 0o755)
        env = dict(os.environ)
        env["PATH"] = f"{fake_bin.as_posix()}:/usr/bin:/bin"
        env["LIMIT_LEVELS_PYTHON_BIN"] = (fake_bin / "fake-python").as_posix()
        env["LIMIT_LEVELS_TIMEOUT_BIN"] = (fake_bin / "timeout").as_posix()
        env["LIMIT_LEVELS_SSH_BIN"] = (fake_bin / "ssh").as_posix()
        env["LIMIT_LEVELS_SCP_BIN"] = (fake_bin / "scp").as_posix()
        env["LIMIT_LEVELS_RETRY_INTERVAL"] = "0"
        git_bash = Path(r"C:\Program Files\Git\bin\bash.exe")

        result = subprocess.run(
            [str(git_bash), wrapper.as_posix(), "--scenario", "normal_progress"],
            env=env, capture_output=True, text=True, encoding="utf-8", timeout=10)

        assert result.returncode == 7
        calls = ssh_calls.read_text(encoding="utf-8")
        assert "run_limit_levels_remote.sh' start" in calls
        assert "run_limit_levels_remote.sh' stop" in calls


def test_evaluation_wrapper_uploads_combined_service_assets():
    text = (HERE / "run_limit_levels_evaluation.sh").read_text(encoding="utf-8")

    assert "server_train/run_limit_levels_service.sh" in text
    assert "server_train/Modelfile.vtg" in text


def test_evaluation_wrapper_accepts_an_alternate_local_evaluator():
    text = (HERE / "run_limit_levels_evaluation.sh").read_text(encoding="utf-8")

    assert "LIMIT_LEVELS_EVAL_SCRIPT" in text
    assert '"$EVAL_SCRIPT" "$@"' in text


if __name__ == "__main__":
    test_runner_is_isolated_to_own_container_and_gpu1()
    test_runner_exposes_start_status_and_stop_actions()
    test_start_timeout_stops_only_the_owned_container()
    test_evaluation_wrapper_stops_remote_container_when_evaluator_fails()
    test_evaluation_wrapper_uploads_combined_service_assets()
    test_evaluation_wrapper_accepts_an_alternate_local_evaluator()
    print("PASS: limit-levels remote runner contract")

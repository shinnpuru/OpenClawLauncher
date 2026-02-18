import subprocess
import threading
import signal
import os
import time
import shutil
import platform
import shlex
from typing import Dict, Optional, IO
from pathlib import Path
from .config import Config
from .install_manager import InstallManager

class ProcessManager:
    """
    Manages running OpenClaw instances.
    Keeps track of processes, handles logging, and lifecycle.
    """
    _instances: Dict[str, subprocess.Popen] = {}
    _logs: Dict[str, IO] = {}

    @classmethod
    def _should_export_env_key(cls, key: str) -> bool:
        managed_keys = {
            "PATH",
            "npm_config_registry",
            "NPM_CONFIG_REGISTRY",
            "pnpm_config_registry",
            "PNPM_CONFIG_REGISTRY",
            "NODEJS_ORG_MIRROR",
            "NVM_NODEJS_ORG_MIRROR",
            "COREPACK_ENABLE_DOWNLOAD_PROMPT",
            "COREPACK_INTEGRITY_KEYS",
            "CI",
        }
        return key in managed_keys or key.startswith("OPENCLAW_") or key.startswith("CLAWDBOT_")

    @classmethod
    def _ensure_cli_openclaw_shim(cls, instance_name: str, instance_path: Path) -> Path:
        script_dir = Config.LOGS_DIR / "_cli_scripts"
        shim_dir = script_dir / "_bin"
        shim_dir.mkdir(parents=True, exist_ok=True)

        safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in instance_name)
        if os.name == "nt":
            shim_path = shim_dir / f"openclaw_{safe_name}.cmd"
            shim_lines = [
                "@echo off",
                "setlocal",
                f'cd /d "{instance_path}"',
                "node openclaw.mjs %*",
                "exit /b %errorlevel%",
            ]
            shim_path.write_text("\r\n".join(shim_lines) + "\r\n", encoding="utf-8")

            active_shim = shim_dir / "openclaw.cmd"
            active_lines = [
                "@echo off",
                f'call "{shim_path}" %*',
                "exit /b %errorlevel%",
            ]
            active_shim.write_text("\r\n".join(active_lines) + "\r\n", encoding="utf-8")
            return shim_dir

        shim_path = shim_dir / f"openclaw_{safe_name}"
        shim_lines = [
            "#!/usr/bin/env bash",
            "set +e",
            f"cd {shlex.quote(str(instance_path))} || exit 1",
            "exec node openclaw.mjs \"$@\"",
        ]
        shim_path.write_text("\n".join(shim_lines) + "\n", encoding="utf-8")
        shim_path.chmod(shim_path.stat().st_mode | 0o111)

        active_shim = shim_dir / "openclaw"
        active_lines = [
            "#!/usr/bin/env bash",
            "set +e",
            f"exec {shlex.quote(str(shim_path))} \"$@\"",
        ]
        active_shim.write_text("\n".join(active_lines) + "\n", encoding="utf-8")
        active_shim.chmod(active_shim.stat().st_mode | 0o111)

        return shim_dir

    @classmethod
    def _build_cli_script(cls, instance_name: str, instance_path: Path, env: dict) -> Path:
        script_dir = Config.LOGS_DIR / "_cli_scripts"
        script_dir.mkdir(parents=True, exist_ok=True)
        cli_shim_dir = cls._ensure_cli_openclaw_shim(instance_name, instance_path)
        env["PATH"] = f"{cli_shim_dir}{os.pathsep}{env.get('PATH', '')}"

        safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in instance_name)
        if os.name == "nt":
            script_path = script_dir / f"{safe_name}_launcher.cmd"
            lines = [
                "@echo off",
                f'cd /d "{instance_path}"',
                f"title OpenClaw CLI - {instance_name}",
            ]
            for key in sorted(env.keys()):
                if cls._should_export_env_key(key):
                    value = str(env.get(key, "")).replace('"', '""')
                    lines.append(f'set "{key}={value}"')
            lines.extend(
                [
                    f"echo OpenClaw instance CLI ready: {instance_name}",
                    f"echo Working directory: {instance_path}",
                ]
            )
            script_path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
            return script_path

        script_path = script_dir / f"{safe_name}_launcher.sh"
        lines = [
            "#!/usr/bin/env bash",
            "set +e",
            f"cd {shlex.quote(str(instance_path))} || exit 1",
        ]
        for key in sorted(env.keys()):
            if cls._should_export_env_key(key):
                value = str(env.get(key, ""))
                lines.append(f"export {key}={shlex.quote(value)}")

        lines.extend(
            [
                f"echo \"OpenClaw instance CLI ready: {instance_name}\"",
                "echo \"Environment loaded from runtime + .env.local\"",
                f"echo \"Working directory: {instance_path}\"",
                "exec \"${SHELL:-/bin/bash}\" -i",
            ]
        )
        script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        script_path.chmod(script_path.stat().st_mode | 0o111)
        return script_path

    @classmethod
    def launch_instance_cli(cls, instance_name: str, instance_path: Path):
        if not instance_path.exists() or not instance_path.is_dir():
            raise FileNotFoundError(f"Instance directory not found: {instance_path}")

        InstallManager.setup_instance_environment(instance_path, instance_name)
        env = InstallManager.get_runtime_env(instance_path=instance_path, instance_name=instance_name)
        script_path = cls._build_cli_script(instance_name, instance_path, env)

        system = platform.system()
        if system == "Darwin":
            subprocess.Popen(["open", "-a", "Terminal", str(script_path)])
            return

        if system == "Windows":
            subprocess.Popen(["cmd", "/c", "start", "", "cmd", "/k", str(script_path)])
            return

        script_cmd = f"bash -lc 'source {shlex.quote(str(script_path))}'"
        terminal_commands = [
            ["x-terminal-emulator", "-e", script_cmd],
            ["gnome-terminal", "--", "bash", "-lc", f"source {shlex.quote(str(script_path))}"],
            ["konsole", "-e", "bash", "-lc", f"source {shlex.quote(str(script_path))}"],
            ["xfce4-terminal", "-e", script_cmd],
            ["xterm", "-e", "bash", "-lc", f"source {shlex.quote(str(script_path))}"],
        ]

        for command in terminal_commands:
            if shutil.which(command[0]):
                subprocess.Popen(command)
                return

        raise RuntimeError("No supported terminal emulator found for launching instance CLI.")

    @classmethod
    def start_instance(cls, instance_name: str, instance_path: Path):
        """Start an OpenClaw instance."""
        if instance_name in cls._instances and cls._instances[instance_name].poll() is None:
            raise RuntimeError(f"Instance '{instance_name}' is already running.")

        openclaw_script = instance_path / "openclaw.mjs"
        if not openclaw_script.exists():
            raise FileNotFoundError(f"openclaw CLI entry not found at {openclaw_script}.")
        
        log_file_path = Config.get_log_file(instance_name)
        log_file = open(log_file_path, "a", encoding="utf-8", buffering=1)
        
        # Prepare environment
        InstallManager.setup_instance_environment(instance_path, instance_name)
        env = InstallManager.get_runtime_env(instance_path=instance_path, instance_name=instance_name)
        instance_port = InstallManager.get_instance_port(instance_path)

        command = ["openclaw", "gateway", "--port", str(instance_port), "--verbose", "--allow-unconfigured"]
        if shutil.which("openclaw", path=env.get("PATH", "")) is None:
            command = ["node", "openclaw.mjs", "gateway", "--port", str(instance_port), "--verbose", "--allow-unconfigured"]

        log_file.write("\n===== Instance runtime started =====\n")
        log_file.write(f"cwd: {instance_path}\n")
        log_file.write(f"command: {' '.join(command)}\n")
        log_file.write(f"runtime node bin: {env.get('OPENCLAW_RUNTIME_NODE_BIN', '')}\n")
        log_file.write(f"runtime uv bin: {env.get('OPENCLAW_RUNTIME_UV_BIN', '')}\n")
        log_file.write(f"runtime python bin: {env.get('OPENCLAW_RUNTIME_PYTHON_BIN', '')}\n")
        path_preview = env.get("PATH", "")
        log_file.write(f"PATH preview: {path_preview[:600]}\n")
        log_file.flush()
        
        # Launch process
        process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            cwd=str(instance_path),
            env=env,
            text=True,
            bufsize=1
        )
        
        cls._instances[instance_name] = process
        cls._logs[instance_name] = log_file
        
        return process

    @classmethod
    def stop_instance(cls, instance_name: str):
        """Stop a running instance."""
        process = cls._instances.get(instance_name)
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            
        if instance_name in cls._logs:
            try:
                cls._logs[instance_name].write("===== Instance runtime stopped =====\n")
                cls._logs[instance_name].flush()
            except Exception:
                pass
            cls._logs[instance_name].close()
            del cls._logs[instance_name]
            
        if instance_name in cls._instances:
            del cls._instances[instance_name]

    @classmethod
    def get_status(cls, instance_name: str) -> str:
        """Get status of an instance."""
        process = cls._instances.get(instance_name)
        if process is None:
            return "Stopped"
        if process.poll() is not None:
             # Clean up
            cls.stop_instance(instance_name)
            return "Stopped (Exited)"
        return "Running"

    @classmethod
    def has_running_instances(cls) -> bool:
        """Return True if any tracked instance process is still running."""
        for instance_name in list(cls._instances.keys()):
            if cls.get_status(instance_name) == "Running":
                return True
        return False

    @classmethod
    def stop_all_instances(cls):
        """Stop all running instances and close all log handles."""
        for instance_name in list(cls._instances.keys()):
            try:
                cls.stop_instance(instance_name)
            except Exception:
                pass

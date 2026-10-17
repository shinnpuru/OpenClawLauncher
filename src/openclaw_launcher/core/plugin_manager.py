"""Read installed plugins from OpenClaw's registry, excluding leftover projects."""

import json
import subprocess
from pathlib import Path

from .install_manager import InstallManager


def list_installed_plugins(instance_path: Path, instance_name: str) -> list[dict]:
    env = InstallManager.get_runtime_env(instance_path, instance_name)
    node = InstallManager.resolve_runtime_tool(env, "node")
    result = subprocess.run(
        [node, "openclaw.mjs", "plugins", "list", "--json"],
        cwd=str(instance_path), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    payload = json.loads(result.stdout)
    records = payload.get("plugins")
    if not isinstance(records, list):
        raise ValueError("OpenClaw returned an invalid plugin list")
    plugins = []
    for record in records:
        if record.get("origin") == "bundled" or not record.get("id"):
            continue
        root = record.get("rootDir")
        if not root:
            continue
        root = Path(root)
        package = root / "package.json"
        if not package.is_file():
            continue
        data = json.loads(package.read_text(encoding="utf-8"))
        plugins.append({
            "id": record["id"],
            "name": data.get("name") or record.get("name") or record["id"],
            "version": record.get("version") or data.get("version", ""),
            "path": root,
        })
    return plugins

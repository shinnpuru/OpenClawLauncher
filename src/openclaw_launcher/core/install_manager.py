import shutil
import subprocess
import os
import logging
import json
import re
import secrets
from pathlib import Path
from typing import Optional, TextIO
from .config import Config
from .runtime_manager import RuntimeManager

logger = logging.getLogger(__name__)

class InstallManager:
    """
    Manages creating instances from installed runtimes.
    """
    
    @staticmethod
    def _parse_semver(version: str):
        if not version:
            return (0, 0, 0)

        normalized = version.strip().lstrip("v")
        normalized = normalized.split("-", 1)[0]
        parts = normalized.split(".")

        parsed = []
        for idx in range(3):
            if idx < len(parts):
                token = re.sub(r"[^0-9]", "", parts[idx])
                parsed.append(int(token) if token else 0)
            else:
                parsed.append(0)

        return tuple(parsed)

    @classmethod
    def _version_gte(cls, current: str, minimum: str) -> bool:
        return cls._parse_semver(current) >= cls._parse_semver(minimum)

    @staticmethod
    def _normalize_registry(registry: Optional[str]) -> str:
        if not isinstance(registry, str):
            return ""
        return registry.strip()

    @classmethod
    def _get_best_installed_node_version(cls, rm: RuntimeManager):
        installed = rm.get_installed_versions(RuntimeManager.SOFTWARE_NODE)
        if not installed:
            return None

        return max(
            (item.get("version") for item in installed if item.get("version")),
            key=cls._parse_semver,
            default=None,
        )

    @classmethod
    def _get_required_node_version(cls, instance_path: Path) -> str:
        default_required = "22.12.0"
        package_json = instance_path / "package.json"
        if not package_json.exists():
            return default_required

        try:
            package_data = json.loads(package_json.read_text(encoding="utf-8"))
            required_expr = package_data.get("engines", {}).get("node", "")
            if not required_expr:
                return default_required

            match = re.search(r">=\s*v?([0-9]+(?:\.[0-9]+){0,2})", required_expr)
            if not match:
                return default_required

            found = match.group(1)
            parts = found.split(".")
            while len(parts) < 3:
                parts.append("0")
            return ".".join(parts[:3])
        except Exception:
            return default_required

    @classmethod
    def ensure_node_runtime(cls, instance_path: Path):
        """Ensure installed Node runtime satisfies package engines requirement."""
        rm = RuntimeManager()
        required = cls._get_required_node_version(instance_path)
        current = cls._get_best_installed_node_version(rm)

        if current and cls._version_gte(current, required):
            return

        available = rm.get_available_versions(RuntimeManager.SOFTWARE_NODE)
        candidates = sorted(
            [item.get("version") for item in available if item.get("version")],
            key=cls._parse_semver,
            reverse=True,
        )

        target = next((ver for ver in candidates if cls._version_gte(ver, required)), None)
        if not target:
            raise RuntimeError(f"No available Node runtime satisfies >= {required}")

        logger.info(f"Installing Node runtime {target} (required >= {required})")
        rm.install_version(RuntimeManager.SOFTWARE_NODE, target)

    @classmethod
    def get_runtime_env(cls, instance_path: Path = None, instance_name: str = None) -> dict:
        """Construct environment variables with runtime paths and instance settings."""
        env = os.environ.copy()
        rm = RuntimeManager()
        
        paths_to_add = []
        python_bin_dir = None
        node_bin_dir = None
        uv_bin_dir = None
        
        # Python
        py_ver = rm.get_default_version(RuntimeManager.SOFTWARE_PYTHON)
        if py_ver:
            # get_executable_path returns the executable file, we need the directory (bin)
            exe_path = rm.get_executable_path(RuntimeManager.SOFTWARE_PYTHON, py_ver)
            python_bin_dir = exe_path.parent
            paths_to_add.append(str(python_bin_dir))

        # Node
        node_ver = rm.get_default_version(RuntimeManager.SOFTWARE_NODE)
        if node_ver:
            exe_path = rm.get_executable_path(RuntimeManager.SOFTWARE_NODE, node_ver)
            node_bin_dir = exe_path.parent
            paths_to_add.append(str(node_bin_dir))
             
        # UV
        uv_ver = rm.get_default_version(RuntimeManager.SOFTWARE_UV)
        if uv_ver:
             exe_path = rm.get_executable_path(RuntimeManager.SOFTWARE_UV, uv_ver)
             uv_bin_dir = exe_path.parent
             paths_to_add.append(str(uv_bin_dir))
        
        if paths_to_add:
            # Prepend to PATH
            env["PATH"] = os.pathsep.join(paths_to_add) + os.pathsep + env.get("PATH", "")

        if instance_path:
            node_bin = instance_path / "node_modules" / ".bin"
            if node_bin.exists():
                env["PATH"] = str(node_bin) + os.pathsep + env.get("PATH", "")

            instance_env = cls._read_instance_env_entries(instance_path)
            if instance_env:
                env.update(instance_env)

        npm_registry = cls._normalize_registry(Config.get_setting("npm_registry", ""))
        if npm_registry:
            env["npm_config_registry"] = npm_registry
            env["NPM_CONFIG_REGISTRY"] = npm_registry
            env["pnpm_config_registry"] = npm_registry
            env["PNPM_CONFIG_REGISTRY"] = npm_registry
            env["COREPACK_NPM_REGISTRY"] = npm_registry

        node_mirror = Config.get_setting("node_mirror", "")
        if isinstance(node_mirror, str):
            node_mirror = node_mirror.strip().rstrip("/")
        else:
            node_mirror = ""
        if node_mirror:
            env["NODEJS_ORG_MIRROR"] = node_mirror
            env["NVM_NODEJS_ORG_MIRROR"] = node_mirror

        env["COREPACK_ENABLE_DOWNLOAD_PROMPT"] = "0"
        env["CI"] = "1"
        env["COREPACK_INTEGRITY_KEYS"] = "0"

        if node_bin_dir:
            env["OPENCLAW_RUNTIME_NODE_BIN"] = str(node_bin_dir)
        if python_bin_dir:
            env["OPENCLAW_RUNTIME_PYTHON_BIN"] = str(python_bin_dir)
        if uv_bin_dir:
            env["OPENCLAW_RUNTIME_UV_BIN"] = str(uv_bin_dir)

        if instance_name:
            env["OPENCLAW_PROFILE"] = instance_name
            env["CLAWDBOT_PROFILE"] = instance_name

        if instance_path:
            resolved_instance_name = instance_name or instance_path.name
            env["OPENCLAW_HOME"] = str(instance_path)
            env["OPENCLAW_GATEWAY_TOKEN"] = cls.get_instance_gateway_token(
                instance_path,
                resolved_instance_name,
            )
            
        return env

    @classmethod
    def _read_instance_env_value(cls, instance_path: Path, key: str) -> Optional[str]:
        env_file = instance_path / ".env.local"
        if not env_file.exists():
            return None

        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                k, value = stripped.split("=", 1)
                if k.strip() == key:
                    parsed = value.strip()
                    return parsed or None
        except Exception:
            return None

        return None

    @classmethod
    def _read_instance_env_entries(cls, instance_path: Path) -> dict:
        env_file = instance_path / ".env.local"
        if not env_file.exists():
            return {}

        entries = {}
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                parsed_key = key.strip()
                if not parsed_key:
                    continue
                entries[parsed_key] = value.strip().strip('"').strip("'")
        except Exception:
            return {}

        return entries

    @classmethod
    def get_instance_gateway_token(cls, instance_path: Path, instance_name: str) -> str:
        token = cls._read_instance_env_value(instance_path, "OPENCLAW_GATEWAY_TOKEN")
        if token:
            return token

        global_token = Config.get_setting("openclaw_gateway_token", "")
        if isinstance(global_token, str):
            global_token = global_token.strip()
            if global_token:
                return global_token

        fallback_token = Config.get_setting("gateway_token", "")
        if isinstance(fallback_token, str):
            fallback_token = fallback_token.strip()
            if fallback_token:
                return fallback_token

        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "", instance_name) or "instance"
        return f"{safe_name}-{secrets.token_urlsafe(24)}"

    @classmethod
    def _find_runtime_tool(cls, env: dict, tool_name: str) -> str:
        """Resolve runtime Node tool path, preferring runtime binaries over system ones."""
        runtime_bin = env.get("OPENCLAW_RUNTIME_NODE_BIN", "").strip()
        candidates = []

        if runtime_bin:
            base = Path(runtime_bin)
            if os.name == "nt":
                candidates.extend([
                    base / f"{tool_name}.cmd",
                    base / f"{tool_name}.exe",
                    base / tool_name,
                ])
            else:
                candidates.append(base / tool_name)

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return str(candidate)

        fallback = shutil.which(tool_name, path=env.get("PATH", ""))
        if fallback:
            return fallback

        raise FileNotFoundError(f"{tool_name} not found in runtime environment")

    @classmethod
    def _run_pnpm(cls, instance_path: Path, args: list[str], env: dict, log_stream: Optional[TextIO] = None):
        kwargs = {
            "cwd": instance_path,
            "env": env,
            "check": True,
            "text": True,
        }
        if log_stream is not None:
            kwargs["stdout"] = log_stream
            kwargs["stderr"] = subprocess.STDOUT

        pnpm_runner = None
        effective_args = list(args)

        has_registry_arg = any(
            arg == "--registry" or arg.startswith("--registry=")
            for arg in effective_args
        )
        if not has_registry_arg:
            registry = cls._normalize_registry(
                env.get("pnpm_config_registry")
                or env.get("PNPM_CONFIG_REGISTRY")
                or env.get("npm_config_registry")
                or env.get("NPM_CONFIG_REGISTRY")
            )
            if registry:
                effective_args.append(f"--registry={registry}")

        try:
            pnpm_cmd = cls._find_runtime_tool(env, "pnpm")
            pnpm_runner = [pnpm_cmd]
        except FileNotFoundError:
            try:
                corepack_cmd = cls._find_runtime_tool(env, "corepack")
            except FileNotFoundError as exc:
                raise FileNotFoundError(
                    "pnpm is not available in current runtime and corepack is missing. "
                    "Please ensure Node runtime is installed from Dependencies, "
                    "or provide pnpm/corepack in PATH."
                ) from exc

            try:
                subprocess.run([corepack_cmd, "enable"], **kwargs)
                subprocess.run([corepack_cmd, "prepare", "pnpm@latest", "--activate"], **kwargs)
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f"Failed to install pnpm via corepack: {exc}") from exc

            try:
                pnpm_cmd = cls._find_runtime_tool(env, "pnpm")
                pnpm_runner = [pnpm_cmd]
            except FileNotFoundError:
                pnpm_runner = [corepack_cmd, "pnpm"]

        subprocess.run([*pnpm_runner, *effective_args], **kwargs)

        if log_stream is not None:
            log_stream.flush()

    @classmethod
    def setup_instance_environment(cls, instance_path: Path, instance_name: str, instance_port: Optional[int] = None):
        """Prepare instance runtime/system environment variables and local env file."""
        env = cls.get_runtime_env(instance_path=instance_path, instance_name=instance_name)

        if instance_port is None:
            instance_port = cls.get_instance_port(instance_path)
        gateway_token = cls.get_instance_gateway_token(instance_path, instance_name)

        env_file = instance_path / ".env.local"
        env_entries = {
            "OPENCLAW_PROFILE": instance_name,
            "CLAWDBOT_PROFILE": instance_name,
            "OPENCLAW_HOME": str(instance_path),
            "OPENCLAW_PORT": str(instance_port),
            "OPENCLAW_GATEWAY_TOKEN": gateway_token
        }

        existing_lines = []
        if env_file.exists():
            existing_lines = env_file.read_text(encoding="utf-8").splitlines()

        preserved_lines = []
        managed_keys = set(env_entries.keys())
        for line in existing_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                preserved_lines.append(line)
                continue

            key = stripped.split("=", 1)[0].strip()
            if key not in managed_keys:
                preserved_lines.append(line)

        for key, value in env_entries.items():
            preserved_lines.append(f"{key}={value}")

        (instance_path / "config").mkdir(parents=True, exist_ok=True)
        (instance_path / "workspace").mkdir(parents=True, exist_ok=True)

        env_file.write_text("\n".join(preserved_lines).rstrip() + "\n", encoding="utf-8")
        return env

    @classmethod
    def get_instance_port(cls, instance_path: Path, default_port: int = 18789) -> int:
        """Read instance port from .env.local, falling back to default when missing/invalid."""
        env_file = instance_path / ".env.local"
        if not env_file.exists():
            return default_port

        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                if key.strip() != "OPENCLAW_PORT":
                    continue

                port = int(value.strip())
                if 1 <= port <= 65535:
                    return port
                return default_port
        except Exception:
            return default_port

        return default_port

    @classmethod
    def install_dependencies(cls, instance_path: Path, instance_name: str, log_stream: Optional[TextIO] = None):
        """Install Node dependencies during instance initialization."""
        env = cls.get_runtime_env(instance_path=instance_path, instance_name=instance_name)
        
        logger.info(f"Installing dependencies in {instance_path}")
        cls._run_pnpm(instance_path, ["install"], env, log_stream=log_stream)

    @classmethod
    def apply_windows_a2ui_patch(cls, instance_path: Path, log_stream: Optional[TextIO] = None):
        """Apply the Windows A2UI placeholder bundle patch before installing deps."""
        if os.name != "nt":
            return

        script_dir = instance_path / "scripts"
        script_dir.mkdir(parents=True, exist_ok=True)
        script_path = script_dir / "bundle-a2ui.mjs"

        placeholder_content = "\n".join(
            [
                "// scripts/bundle-a2ui.mjs",
                "// OpenClaw A2UI Bundle Placeholder Generator",
                "// For public repository users who do not have access to private A2UI source code.",
                "// This script creates a minimal valid ES module to satisfy TypeScript compilation.",
                "",
                "import fs from 'node:fs';",
                "import path from 'node:path';",
                "import { createHash } from 'node:crypto';",
                "import { fileURLToPath } from 'node:url';",
                "",
                "// Resolve project root directory correctly on Windows and Unix.",
                "const __filename = fileURLToPath(import.meta.url);",
                "const __dirname = path.dirname(__filename);",
                "const ROOT_DIR = path.resolve(__dirname, '..'); // openclaw/ root",
                "",
                "// Define output paths.",
                "const OUTPUT_DIR = path.join(ROOT_DIR, 'src', 'canvas-host', 'a2ui');",
                "const OUTPUT_FILE = path.join(OUTPUT_DIR, 'a2ui.bundle.js');",
                "const HASH_FILE = path.join(OUTPUT_DIR, '.bundle.hash');",
                "",
                "// Ensure output directory exists.",
                "fs.mkdirSync(OUTPUT_DIR, { recursive: true });",
                "",
                "// Generate placeholder content (valid ES module).",
                "const placeholderContent = `",
                "// Auto-generated placeholder for A2UI",
                "// Source code is not available in the public OpenClaw repository.",
                "// This file exists only to satisfy build dependencies.",
                "export const A2UI = {",
                "  version: '0.0.0-placeholder',",
                "  render: () => {",
                "    throw new Error('A2UI runtime is not available in this build.');",
                "  }",
                "};",
                "`.trim() + '\\n';",
                "",
                "// Write the bundle file.",
                "fs.writeFileSync(OUTPUT_FILE, placeholderContent);",
                "",
                "// Compute and write hash to prevent unnecessary rebuilds.",
                "const hash = createHash('sha256').update(placeholderContent).digest('hex');",
                "fs.writeFileSync(HASH_FILE, hash);",
                "",
                "// Success message.",
                "console.log('A2UI placeholder bundle created successfully.');",
                "console.log(`   Bundle: ${OUTPUT_FILE}`);",
                "console.log(`   Hash:   ${HASH_FILE}`);",
                "",
            ]
        )

        script_path.write_text(placeholder_content, encoding="utf-8")

        package_json = instance_path / "package.json"
        if package_json.exists():
            try:
                package_data = json.loads(package_json.read_text(encoding="utf-8"))
                scripts = package_data.get("scripts")
                if not isinstance(scripts, dict):
                    scripts = {}
                    package_data["scripts"] = scripts
                desired = "node --import tsx scripts/bundle-a2ui.mjs"
                if scripts.get("canvas:a2ui:bundle") != desired:
                    scripts["canvas:a2ui:bundle"] = desired
                    package_json.write_text(json.dumps(package_data, indent=2) + "\n", encoding="utf-8")
            except Exception as exc:
                raise RuntimeError(f"Failed to apply A2UI patch: {exc}") from exc

        if log_stream is not None:
            log_stream.write("Applied Windows A2UI placeholder patch.\n")
            log_stream.flush()

    @classmethod
    def build_frontend(cls, instance_path: Path, instance_name: str, log_stream: Optional[TextIO] = None):
        """Build the UI components."""
        logger.info(f"Building UI in {instance_path}")
        env = cls.get_runtime_env(instance_path=instance_path, instance_name=instance_name)
        cls._run_pnpm(instance_path, ["ui:build"], env, log_stream=log_stream)

    @classmethod
    def build_backend(cls, instance_path: Path, instance_name: str, log_stream: Optional[TextIO] = None):
        """Build the backend/application."""
        logger.info(f"Building OpenClaw in {instance_path}")
        env = cls.get_runtime_env(instance_path=instance_path, instance_name=instance_name)
        cls._run_pnpm(instance_path, ["build"], env, log_stream=log_stream)
        
    @classmethod
    def complete_install(cls, instance_name: str, instance_port: int = 18789, repo_url=None):
        """
        Creates a new instance by copying from the cached OpenClaw runtime.
        """
        Config.ensure_dirs()
        target_path = Config.get_instance_path(instance_name)
        
        if target_path.exists():
            raise FileExistsError(f"Instance {instance_name} already exists.")

        rm = RuntimeManager()
        oc_ver = rm.get_default_version(RuntimeManager.SOFTWARE_OPENCLAW)
        if not oc_ver:
             raise RuntimeError("No OpenClaw runtime downloaded. Please download it from Dependencies tab.")
             
        source_path = rm.get_runtime_path(RuntimeManager.SOFTWARE_OPENCLAW, oc_ver)
        if not source_path.exists():
             raise RuntimeError(f"OpenClaw source path not found: {source_path}")

        logger.info(f"Creating instance {instance_name} from {source_path}")
        
        shutil.copytree(source_path, target_path, ignore=shutil.ignore_patterns('node_modules', '.env'), symlinks=True)
        
        log_file_path = Config.get_log_file(instance_name)
        log_file = open(log_file_path, "a", encoding="utf-8")

        try:
            log_file.write("\n===== Instance bootstrap started =====\n")
            log_file.flush()

            cls.ensure_node_runtime(target_path)
            cls.setup_instance_environment(target_path, instance_name, instance_port=instance_port)

            if Config.get_setting("windows_a2ui_patch", False):
                cls.apply_windows_a2ui_patch(target_path, log_stream=log_file)

            cls.install_dependencies(target_path, instance_name, log_stream=log_file)
            cls.build_frontend(target_path, instance_name, log_stream=log_file)
            cls.build_backend(target_path, instance_name, log_stream=log_file)

            log_file.write("===== Instance bootstrap completed =====\n")
            log_file.flush()
            logger.info(f"Installation of {instance_name} complete.")
        except Exception as e:
            log_file.write(f"Installation failed: {e}\n")
            log_file.flush()
            logger.error(f"Installation failed, cleaning up: {e}")
            if target_path.exists():
                shutil.rmtree(target_path)
            raise e
        finally:
            log_file.close()
            
        return target_path

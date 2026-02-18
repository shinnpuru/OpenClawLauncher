import subprocess
import os
import sys
import shutil
import platform
import logging
from typing import Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

def run_command(cmd: List[str], cwd: Optional[Path] = None, env: Optional[dict] = None, check: bool = True) -> Tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        logger.info(f"Running command: {' '.join(cmd)} in {cwd or os.getcwd()}")
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env or os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if check and result.returncode != 0:
            logger.error(f"Command failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        logger.error(f"Command not found: {cmd[0]}")
        raise

def is_tool_installed(name: str) -> bool:
    """Check if a tool is installed and available in PATH."""
    return shutil.which(name) is not None

def get_node_version() -> Optional[str]:
    """Get the installed Node.js version."""
    if not is_tool_installed("node"):
        return None
    try:
        code, out, _ = run_command(["node", "-v"], check=False)
        if code == 0:
            return out.strip().lstrip("v")
    except Exception:
        pass
    return None

def open_file_explorer(path: Path):
    """Open the file explorer at the given path."""
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.run(["open", path])
    else:  # Linux
        subprocess.run(["xdg-open", path])

def install_system_dependency(tool_name: str, package_name: str = None):
    """Simple wrapper to try installing system dependencies (brew, apt)."""
    if package_name is None:
        package_name = tool_name
        
    os_name = platform.system()
    if os_name == "Darwin" and is_tool_installed("brew"):
        run_command(["brew", "install", package_name])
    elif os_name == "Linux":
        # Simplified, usually requires sudo/auth
        if is_tool_installed("apt-get"):
            run_command(["sudo", "apt-get", "install", "-y", package_name])
        elif is_tool_installed("dnf"):
            run_command(["sudo", "dnf", "install", "-y", package_name])
        elif is_tool_installed("pacman"):
             run_command(["sudo", "pacman", "-S", "--noconfirm", package_name])
    elif os_name == "Windows" and is_tool_installed("choco"):
        run_command(["choco", "install", package_name, "-y"])
    else:
        raise OSError(f"Cannot auto-install {tool_name} on this system. Please install manually.")

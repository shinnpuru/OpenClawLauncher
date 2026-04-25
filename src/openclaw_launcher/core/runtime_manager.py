import os
import json
import logging
import platform
import shutil
import tarfile
import zipfile
import urllib.request
import urllib.parse
import ssl
import sys
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from .config import Config

logger = logging.getLogger(__name__)

class RuntimeManager:
    """
    Manages the resulting runtime downloads and installations.
    """
    ROOT_DIR = Path(os.getcwd())
    RUNTIME_BASE_DIR = ROOT_DIR / "runtime"
    
    SOFTWARE_PYTHON = "python"
    SOFTWARE_NODE = "node"
    SOFTWARE_UV = "uv"
    SOFTWARE_OPENCLAW = "openclaw"
    OPENCLAW_VERSIONS_CONFIG_KEY = "openclaw_available_versions"
    OPENCLAW_VERSIONS_REFRESHED_AT_CONFIG_KEY = "openclaw_available_versions_refreshed_at"

    def __init__(self):
        self.ensure_dirs()
        self._os = platform.system().lower()
        self._arch = platform.machine().lower()
        self._remote_versions_cache: Dict[str, List[Dict]] = {}
        self._remote_versions_refreshed_at: Dict[str, str] = {}
        # Mapping definitions
        self._available_versions = {
            self.SOFTWARE_PYTHON: [
                {"version": "3.10.11", "date": "2023-04-05", "tag": "20230507"},
                {"version": "3.12.1", "date": "2023-12-08", "tag": "20240107"}
            ],
            self.SOFTWARE_NODE: [
                {"version": "22.22.1", "date": "2026-03-05"},
                {"version": "24.14.0", "date": "2026-02-24"},
                {"version": "25.8.1", "date": "2026-03-11"},
            ],
            self.SOFTWARE_UV: [
                {"version": "0.10.10", "date": "2026-03-13"}
            ],
            self.SOFTWARE_OPENCLAW: []
        }

        self._remote_versions_cache[self.SOFTWARE_OPENCLAW] = self._load_cached_openclaw_versions()
        refreshed_at = Config.get_setting(self.OPENCLAW_VERSIONS_REFRESHED_AT_CONFIG_KEY, "")
        if isinstance(refreshed_at, str):
            refreshed_at = refreshed_at.strip()
            if refreshed_at:
                self._remote_versions_refreshed_at[self.SOFTWARE_OPENCLAW] = refreshed_at

    def _load_cached_openclaw_versions(self) -> List[Dict]:
        value = Config.get_setting(self.OPENCLAW_VERSIONS_CONFIG_KEY, [])
        if not isinstance(value, list):
            return []

        normalized: List[Dict] = []
        for item in value:
            if not isinstance(item, dict):
                continue

            version = str(item.get("version", "")).strip()
            if not version:
                continue

            date = str(item.get("date", "Unknown")).strip() or "Unknown"
            if date == "Unknown":
                date = self._date_from_openclaw_tag(version)
            url = str(item.get("url", "")).strip()
            entry = {
                "version": version,
                "date": date,
            }
            if url:
                entry["url"] = url
            normalized.append(entry)

        normalized.sort(key=lambda x: self._natural_version_key(x["version"]), reverse=True)
        return normalized

    def _save_cached_openclaw_versions(self, versions: List[Dict]):
        Config.set_setting(self.OPENCLAW_VERSIONS_CONFIG_KEY, versions)

    def ensure_dirs(self):
        self.RUNTIME_BASE_DIR.mkdir(parents=True, exist_ok=True)

    def _runtime_default_key(self, software: str) -> str:
        return f"default_runtime_{software}"

    def _natural_version_key(self, version: str):
        if version == "main":
            return (1, 0)

        parts = []
        token = ""
        for ch in str(version):
            if ch.isdigit():
                token += ch
            else:
                if token:
                    parts.append(int(token))
                    token = ""
        if token:
            parts.append(int(token))

        if not parts:
            return (0, 0)
        return (0, *parts)

    def _date_from_openclaw_tag(self, tag: str) -> str:
        normalized = str(tag).strip().lower()
        if normalized.startswith("v"):
            normalized = normalized[1:]

        match = re.match(r"^(\d{4})[._-](\d{1,2})[._-](\d{1,2})(?:[._-].*)?$", normalized)
        if not match:
            return "Unknown"

        try:
            year, month, day = map(int, match.groups())
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            return "Unknown"

    def _get_github_proxy(self) -> str:
        from .config import Config

        proxy = Config.get_setting("github_proxy", "")
        if not isinstance(proxy, str):
            return ""
        return proxy.strip().rstrip("/")

    def _with_github_proxy(self, url: str) -> str:
        proxy = self._get_github_proxy()
        if not proxy:
            return url

        prefix = "https://github.com"
        if not url.startswith(prefix):
            return url

        return f"{proxy}{url[len(prefix):]}"

    def _get_node_mirror(self) -> str:
        from .config import Config

        mirror = Config.get_setting("node_mirror", "")
        if not isinstance(mirror, str):
            return ""
        return mirror.strip().rstrip("/")

    def _get_download_url(self, software: str, version: str, meta: dict = {}) -> str:
        os_name = self._os
        arch = self._arch

        if software == self.SOFTWARE_PYTHON:
            # Standalone python builds (indygreg)
            tag = meta.get("tag", "20240107")
            
            p_arch = "x86_64"
            if "arm" in arch or "aarch" in arch:
                p_arch = "aarch64"
            
            p_os = "unknown-linux-gnu"
            suffix = "tar.gz"
            if os_name == "darwin":
                p_os = "apple-darwin"
            elif os_name == "windows":
                p_os = "pc-windows-msvc-shared"
                
            filename = f"cpython-{version}+{tag}-{p_arch}-{p_os}-install_only.{suffix}"
            url = f"https://github.com/indygreg/python-build-standalone/releases/download/{tag}/{filename}"
            return self._with_github_proxy(url)

        elif software == self.SOFTWARE_NODE:
            # node-v{ver}-{os}-{arch}.tar.gz
            n_os = os_name
            n_arch = "x64"
            if "arm" in arch or "aarch" in arch:
                n_arch = "arm64"
            
            ext = "tar.gz"
            if os_name == "windows":
                n_os = "win"
                ext = "zip"
            
            filename = f"node-v{version}-{n_os}-{n_arch}.{ext}"
            node_mirror = self._get_node_mirror()
            if node_mirror:
                return f"{node_mirror}/v{version}/{filename}"
            return f"https://nodejs.org/dist/v{version}/{filename}"

        elif software == self.SOFTWARE_UV:
            # uv-{arch}-{os}.tar.gz
            u_arch = "x86_64"
            if "arm" in arch or "aarch" in arch:
                u_arch = "aarch64"
            
            u_os = "unknown-linux-gnu"
            ext = "tar.gz"
            if os_name == "darwin":
                u_os = "apple-darwin"
            elif os_name == "windows":
                u_os = "pc-windows-msvc"
                ext = "zip"

            filename = f"uv-{u_arch}-{u_os}.{ext}"
            url = f"https://github.com/astral-sh/uv/releases/download/{version}/{filename}"
            return self._with_github_proxy(url)
            
        return ""

    def get_installed_versions(self, software: str) -> List[Dict]:
        versions = []
        if not self.RUNTIME_BASE_DIR.exists():
            return versions

        prefix = f"{software}-"
        for item in self.RUNTIME_BASE_DIR.iterdir():
            if item.is_dir() and item.name.startswith(prefix):
                ver_str = item.name[len(prefix):]
                meta_file = item / "install_info.json"
                date_str = "Unknown"
                if meta_file.exists():
                    try:
                        with open(meta_file, 'r') as f:
                            data = json.load(f)
                            date_str = data.get("date", date_str)
                    except:
                        pass
                else:
                    timestamp = item.stat().st_mtime
                    date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')

                versions.append({
                    "version": ver_str,
                    "path": str(item),
                    "date": date_str
                })
        
        versions.sort(key=lambda x: self._natural_version_key(x["version"]), reverse=True)
        return versions

    def get_latest_installed_version(self, software: str) -> Optional[str]:
        versions = self.get_installed_versions(software)
        return versions[0]['version'] if versions else None

    def get_configured_default_version(self, software: str) -> Optional[str]:
        value = Config.get_setting(self._runtime_default_key(software), "")
        if not isinstance(value, str):
            return None

        selected = value.strip()
        if not selected:
            return None

        if not self.is_installed(software, selected):
            return None

        return selected

    def get_default_version(self, software: str) -> Optional[str]:
        configured = self.get_configured_default_version(software)
        if configured:
            return configured
        return self.get_latest_installed_version(software)

    def set_default_version(self, software: str, version: str):
        normalized = (version or "").strip()
        if not normalized:
            raise ValueError("Version cannot be empty")

        if not self.is_installed(software, normalized):
            raise ValueError(f"{software} {normalized} is not installed")

        Config.set_setting(self._runtime_default_key(software), normalized)

    def _find_runtime_npm(self) -> str:
        """Find npm executable from installed Node runtime."""
        node_ver = self.get_default_version(self.SOFTWARE_NODE)
        if not node_ver:
            raise FileNotFoundError("No Node runtime installed")

        exe_path = self.get_executable_path(self.SOFTWARE_NODE, node_ver)
        node_bin_dir = exe_path.parent
        runtime_root = node_bin_dir.parent

        # Look for npm in runtime
        candidates = []
        if platform.system() == "Windows":
            candidates = [
                node_bin_dir / "npm.cmd",
                node_bin_dir / "npm.exe",
                runtime_root / "lib" / "node_modules" / "npm" / "bin" / "npm-cli.js",
            ]
        else:
            candidates = [
                node_bin_dir / "npm",
                runtime_root / "lib" / "node_modules" / "npm" / "bin" / "npm-cli.js",
            ]

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return str(candidate)

        raise FileNotFoundError("npm not found in Node runtime")

    def _fetch_openclaw_versions(self) -> List[Dict]:
        versions = []

        try:
            logger.info("Fetching OpenClaw versions from npm registry")
            npm_cmd = self._find_runtime_npm()
            # If it's a .js file, we need to run it with node
            if npm_cmd.endswith(".js"):
                node_ver = self.get_default_version(self.SOFTWARE_NODE)
                exe_path = self.get_executable_path(self.SOFTWARE_NODE, node_ver)
                cmd = [str(exe_path), npm_cmd, "view", "openclaw", "versions", "--json"]
            else:
                cmd = [npm_cmd, "view", "openclaw", "versions", "--json"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            version_list = json.loads(result.stdout)
            if isinstance(version_list, list):
                # Filter versions that look like valid releases (start with digit) and exclude prerelease versions
                prerelease_keywords = ("beta", "alpha", "rc", "preview", "dev", "canary", "next")
                valid_versions = [
                    v for v in version_list
                    if isinstance(v, str) and v and v[0].isdigit()
                    and not any(keyword in v.lower() for keyword in prerelease_keywords)
                ]
                # Sort and take latest 10
                valid_versions.sort(key=self._natural_version_key, reverse=True)
                valid_versions = valid_versions[:10]

                for ver in valid_versions:
                    versions.append({
                        "version": ver,
                        "date": ver,
                    })

            logger.info(f"Fetched {len(versions)} OpenClaw versions from npm")
        except Exception as e:
            logger.warning(f"Failed to fetch OpenClaw versions from npm: {e}")

        return versions

    def refresh_available_versions(self, software: str):
        if software != self.SOFTWARE_OPENCLAW:
            return

        versions = self._fetch_openclaw_versions()
        self._remote_versions_cache[software] = versions
        refreshed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._remote_versions_refreshed_at[software] = refreshed_at
        self._save_cached_openclaw_versions(versions)
        Config.set_setting(self.OPENCLAW_VERSIONS_REFRESHED_AT_CONFIG_KEY, refreshed_at)

    def get_available_versions_refreshed_at(self, software: str) -> Optional[str]:
        value = self._remote_versions_refreshed_at.get(software)
        return value if value else None

    def get_available_versions(self, software: str) -> List[Dict]:
        if software == self.SOFTWARE_OPENCLAW:
            cached = self._remote_versions_cache.get(software, [])
            return list(cached)

        return self._available_versions.get(software, [])

    def is_installed(self, software: str, version: str) -> bool:
        return (self.RUNTIME_BASE_DIR / f"{software}-{version}").exists()

    def get_runtime_path(self, software: str, version: str) -> Path:
        return self.RUNTIME_BASE_DIR / f"{software}-{version}"

    def _emit_progress(self, callback, stage: str, current: Optional[int] = None, total: Optional[int] = None, message: str = ""):
        if callback is None:
            return

        try:
            callback({
                "stage": stage,
                "current": current,
                "total": total,
                "message": message,
            })
        except Exception:
            pass

    def _download_file(self, url: str, dest: Path, callback=None):
        logger.info(f"Downloading {url} to {dest}")
        try:
             context = ssl._create_unverified_context()
             with urllib.request.urlopen(url, context=context) as response, open(dest, 'wb') as out_file:
                 total_header = response.headers.get("Content-Length")
                 total = int(total_header) if total_header and total_header.isdigit() else None
                 downloaded = 0
                 self._emit_progress(callback, "download", 0, total, f"Downloading {dest.name}")

                 while True:
                     chunk = response.read(1024 * 256)
                     if not chunk:
                         break
                     out_file.write(chunk)
                     downloaded += len(chunk)
                     self._emit_progress(callback, "download", downloaded, total, f"Downloading {dest.name}")
        except AttributeError:
             urllib.request.urlretrieve(url, dest)
             self._emit_progress(callback, "download", 1, 1, f"Downloading {dest.name}")

    def _extract_archive(self, archive_path: Path, dest_dir: Path):
        logger.info(f"Extracting {archive_path} to {dest_dir}")
        temp_extract = dest_dir / "_temp_extract"
        temp_extract.mkdir(parents=True, exist_ok=True)
        
        try:
            if str(archive_path).endswith("tar.gz") or str(archive_path).endswith("tgz"):
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(path=temp_extract)
            elif str(archive_path).endswith("zip"):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract)
            
            # Flatten logic with safe copy to handle long paths and cross-device moves
            def _safe_move(src: Path, dst_dir: Path):
                dst = dst_dir / src.name
                # Ensure destination parent exists
                dst.parent.mkdir(parents=True, exist_ok=True)

                try:
                    if src.is_dir():
                        # Use copytree with dirs_exist_ok to merge/overwrite if needed
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                        try:
                            shutil.rmtree(src)
                        except Exception:
                            pass
                    else:
                        shutil.copy2(src, dst)
                        try:
                            src.unlink()
                        except Exception:
                            pass
                except Exception:
                    # Surface the error so caller can handle/report it
                    raise

            items = list(temp_extract.iterdir())
            if len(items) == 1 and items[0].is_dir():
                source = items[0]
                for item in source.iterdir():
                    _safe_move(item, dest_dir)
            else:
                for item in temp_extract.iterdir():
                    _safe_move(item, dest_dir)
                    
        finally:
            if temp_extract.exists():
                shutil.rmtree(temp_extract)

    def install_version(self, software: str, version: str, callback=None):
        target_dir = self.RUNTIME_BASE_DIR / f"{software}-{version}"
        if target_dir.exists():
            if (target_dir / "install_info.json").exists():
                 logger.info(f"{software} {version} already installed.")
                 self._emit_progress(callback, "done", 1, 1, f"{software} {version} already installed")
                 return
            else:
                 shutil.rmtree(target_dir)

        logger.info(f"Installing {software} {version}...")
        self._emit_progress(callback, "prepare", 0, None, f"Preparing {software} {version}")
        temp_dir = self.RUNTIME_BASE_DIR / "_temp_dl"
        temp_dir.mkdir(exist_ok=True, parents=True)
        
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            
            if software == self.SOFTWARE_OPENCLAW:
                # Use npm pack to download the package
                self._emit_progress(callback, "download", 0, None, f"Downloading openclaw@{version}")
                try:
                    npm_cmd = self._find_runtime_npm()
                    # If it's a .js file, we need to run it with node
                    if npm_cmd.endswith(".js"):
                        node_ver = self.get_default_version(self.SOFTWARE_NODE)
                        exe_path = self.get_executable_path(self.SOFTWARE_NODE, node_ver)
                        cmd = [str(exe_path), npm_cmd, "pack", f"openclaw@{version}"]
                    else:
                        cmd = [npm_cmd, "pack", f"openclaw@{version}"]

                    pack_result = subprocess.run(
                        cmd,
                        cwd=temp_dir,
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=120,
                    )
                    # npm pack outputs the filename to stdout
                    tarball_name = pack_result.stdout.strip().splitlines()[-1].strip()
                    tarball_path = temp_dir / tarball_name

                    if not tarball_path.exists():
                        raise RuntimeError(f"npm pack did not create expected tarball: {tarball_name}")

                    self._emit_progress(callback, "extract", 0, None, f"Extracting {tarball_name}")
                    self._extract_archive(tarball_path, target_dir)
                    self._emit_progress(callback, "extract", 1, 1, f"Extracted {tarball_name}")
                    tarball_path.unlink()
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f"npm pack failed: {e.stderr}") from e
            else:
                meta = next((item for item in self._available_versions.get(software, []) if item["version"] == version), {})
                url = self._get_download_url(software, version, meta)
                
                if not url:
                    raise ValueError(f"No download URL for {software} {version}")
                
                archive_name = url.split("/")[-1]
                dl_path = temp_dir / archive_name
                
                self._download_file(url, dl_path, callback=callback)
                self._emit_progress(callback, "extract", 0, None, f"Extracting {archive_name}")
                self._extract_archive(dl_path, target_dir)
                self._emit_progress(callback, "extract", 1, 1, f"Extracted {archive_name}")
                dl_path.unlink() # Delete archive
                
            with open(target_dir / "install_info.json", "w") as f:
                json.dump({
                    "version": version,
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "timestamp": datetime.now().timestamp(),
                    "source": "download"
                }, f)
            self._emit_progress(callback, "done", 1, 1, f"Installed {software} {version}")
                
        except Exception as e:
            logger.error(f"Installation failed: {e}")
            if target_dir.exists():
                shutil.rmtree(target_dir)
            raise e
        finally:
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass

    def get_executable_path(self, software: str, version: str) -> Path:
        base = self.get_runtime_path(software, version)
        
        if software == self.SOFTWARE_PYTHON:
            if platform.system() == "Windows":
                 found = list(base.rglob("python.exe"))
            else:
                 found = list(base.rglob("bin/python3"))
                 if not found:
                     found = list(base.rglob("bin/python"))
            
            if found:
                return found[0]

        elif software == self.SOFTWARE_NODE:
            if platform.system() == "Windows":
                 found = list(base.rglob("node.exe"))
            else:
                 found = list(base.rglob("bin/node"))
            
            if found:
                return found[0]

        elif software == self.SOFTWARE_UV:
             if platform.system() == "Windows":
                 found = list(base.rglob("uv.exe"))
             else:
                 found = list(base.rglob("uv"))
             
             found = [f for f in found if f.is_file()]
             if found:
                 return found[0]

        return base

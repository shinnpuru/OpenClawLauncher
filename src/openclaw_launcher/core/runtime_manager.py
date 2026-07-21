import os
import json
import logging
import platform
import shutil
import tarfile
import zipfile
import urllib.request
import urllib.parse
import urllib.error
import ssl
import sys
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Iterable
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
                {"version": "24.15.0", "date": "2026-03-12"},
                {"version": "25.9.0", "date": "2026-03-15"},
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

    def _get_npm_registry(self) -> str:
        value = Config.get_setting("npm_registry", "")
        if not isinstance(value, str):
            return ""
        return value.strip().rstrip("/")

    def _normalize_openclaw_versions(
        self,
        version_list: Iterable[str],
        time_map: Optional[Dict[str, str]] = None,
    ) -> List[Dict]:
        prerelease_keywords = ("beta", "alpha", "rc", "preview", "dev", "canary", "next")
        valid_versions = [
            v
            for v in version_list
            if isinstance(v, str)
            and v
            and v[0].isdigit()
            and not any(keyword in v.lower() for keyword in prerelease_keywords)
        ]
        valid_versions.sort(key=self._natural_version_key, reverse=True)
        valid_versions = valid_versions[:10]

        normalized: List[Dict] = []
        for ver in valid_versions:
            date_value = "Unknown"
            if isinstance(time_map, dict):
                raw_time = str(time_map.get(ver, "")).strip()
                if raw_time:
                    # npm registry time field is usually ISO-8601. Keep date portion only.
                    date_value = raw_time[:10]
            if date_value == "Unknown":
                date_value = self._date_from_openclaw_tag(ver)

            normalized.append(
                {
                    "version": ver,
                    "date": date_value,
                }
            )

        return normalized

    def _fetch_openclaw_versions_via_registry(self) -> List[Dict]:
        npm_registry = self._get_npm_registry() or "https://registry.npmjs.org"
        url = f"{npm_registry}/openclaw"

        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "OpenClawLauncher/1.0",
            },
        )

        payload = None
        last_exc: Optional[Exception] = None

        # Try multiple SSL contexts / strategies to work around platform TLS incompatibilities
        contexts: List[ssl.SSLContext] = []
        try:
            contexts.append(ssl._create_unverified_context())
        except Exception:
            pass

        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            try:
                ctx.set_ciphers("DEFAULT@SECLEVEL=1")
            except Exception:
                # set_ciphers may not be available on some platforms
                pass
            contexts.append(ctx)
        except Exception:
            pass

        for ctx in contexts:
            try:
                with urllib.request.urlopen(request, timeout=20, context=ctx) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except Exception as e:
                last_exc = e

        # If HTTP-based fetch failed, try npm as a fallback (if npm/runtime available)
        if payload is None:
            try:
                npm_registry = self._get_npm_registry() or "https://registry.npmjs.org"
                npm_cmd = self._find_runtime_npm()
                node_ver = self.get_default_version(self.SOFTWARE_NODE)
                if node_ver:
                    exe_path = self.get_executable_path(self.SOFTWARE_NODE, node_ver)
                    cmd = [str(exe_path), npm_cmd, "view", "openclaw", "versions", "--json", "--registry", npm_registry]
                    res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
                    versions = json.loads(res.stdout)
                    if isinstance(versions, list):
                        return self._normalize_openclaw_versions(versions)
            except Exception:
                # ignore and re-raise original error below
                pass

            if last_exc:
                raise last_exc
            raise RuntimeError("Failed to fetch OpenClaw registry payload")

        versions_obj = payload.get("versions", {})
        if isinstance(versions_obj, dict):
            versions = list(versions_obj.keys())
        else:
            versions = []

        time_map = payload.get("time", {})
        if not isinstance(time_map, dict):
            time_map = {}

        return self._normalize_openclaw_versions(versions, time_map=time_map)

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

    def uninstall_version(self, software: str, version: str) -> bool:
        """Remove a downloaded runtime from disk.

        Returns True when the deleted version was the configured default
        (so the caller can inform the user that a new default is auto-selected).
        """
        normalized = (version or "").strip()
        if not normalized:
            raise ValueError("Version cannot be empty")

        target_dir = self.get_runtime_path(software, normalized)
        if not target_dir.exists() and not target_dir.is_symlink():
            raise FileNotFoundError(f"{software} {normalized} is not installed")

        was_default = self.get_configured_default_version(software) == normalized
        self._delete_path(target_dir)

        if was_default:
            Config.set_setting(self._runtime_default_key(software), "")

        return was_default

    def _find_runtime_npm(self) -> str:
        """Find npm executable from installed Node runtime."""
        node_ver = self.get_default_version(self.SOFTWARE_NODE)
        if not node_ver:
            raise FileNotFoundError("No Node runtime installed")

        exe_path = self.get_executable_path(self.SOFTWARE_NODE, node_ver)
        node_bin_dir = exe_path.parent
        runtime_root = node_bin_dir.parent

        # Look for npm in runtime
        candidates = [
            node_bin_dir / "node_modules" / "npm" / "bin" / "npm-cli.js",
            runtime_root / "lib" / "node_modules" / "npm" / "bin" / "npm-cli.js",
        ]

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return str(candidate)

        raise FileNotFoundError("npm not found in Node runtime")

    def _fetch_openclaw_versions(self) -> Optional[List[Dict]]:
        logger.info("Fetching OpenClaw versions from npm registry")

        try:
            registry_versions = self._fetch_openclaw_versions_via_registry()
            logger.info(f"Fetched {len(registry_versions)} OpenClaw versions from npm registry API")
            return registry_versions
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as registry_error:
            logger.warning(f"Failed to fetch OpenClaw versions from npm registry API: {registry_error}")
        except Exception as registry_error:
            logger.warning(f"Unexpected error while fetching OpenClaw versions from npm registry API: {registry_error}")

        return None

    def refresh_available_versions(self, software: str):
        if software != self.SOFTWARE_OPENCLAW:
            return

        versions = self._fetch_openclaw_versions()
        if versions is None:
            logger.warning("OpenClaw versions refresh failed; keeping previously cached versions")
            return

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

    @classmethod
    def _delete_path(cls, path: Path):
        if not path.exists() and not path.is_symlink():
            return

        try:
            if path.is_dir() and not path.is_symlink():
                for child in path.iterdir():
                    cls._delete_path(child)
                path.rmdir()
            else:
                path.unlink()
        except FileNotFoundError:
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
        if str(archive_path).endswith("tar.gz") or str(archive_path).endswith("tgz"):
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=dest_dir)
        elif str(archive_path).endswith("zip"):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)
        else:
            raise ValueError(f"Unsupported archive format: {archive_path}")

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
                    node_ver = self.get_default_version(self.SOFTWARE_NODE)
                    if not node_ver:
                        raise RuntimeError("No Node runtime installed")
                    exe_path = self.get_executable_path(self.SOFTWARE_NODE, node_ver)
                    cmd = [str(exe_path), npm_cmd, "pack", f"openclaw@{version}"]

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

                    final_tarball = target_dir / tarball_name
                    shutil.move(str(tarball_path), str(final_tarball))
                    self._emit_progress(callback, "extract", 1, 1, f"Downloaded {tarball_name}")
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
                self._delete_path(target_dir)
            raise e
        finally:
            if temp_dir.exists():
                try:
                    self._delete_path(temp_dir)
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

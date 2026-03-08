from __future__ import annotations

import argparse
import json
import shutil
import ssl
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path


LLAMA_CPP_RELEASES_API = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
TARGETS = {
    "win-vulkan-x64": {
        "archive_name_template": "llama-{tag}-bin-win-vulkan-x64.zip",
        "executable": "llama-server.exe",
    },
    "macos-arm64": {
        "archive_name_template": "llama-{tag}-bin-macos-arm64.tar.gz",
        "executable": "llama-server",
    },
    "win-cuda-12.4-x64": {
        "archive_name_template": "llama-{tag}-bin-win-cuda-12.4-x64.zip",
        "extra_archive_name_templates": [
            "cudart-llama-bin-win-cuda-12.4-x64.zip",
        ],
        "executable": "llama-server.exe",
    },
}


def _download_file(url: str, destination: Path):
    context = ssl._create_unverified_context()
    request = urllib.request.Request(url, headers={"User-Agent": "openclaw-launcher-build"})
    with urllib.request.urlopen(request, context=context, timeout=120) as response:
        destination.write_bytes(response.read())


def get_latest_llama_cpp_tag() -> str:
    context = ssl._create_unverified_context()
    request = urllib.request.Request(
        LLAMA_CPP_RELEASES_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "openclaw-launcher-build"},
    )
    with urllib.request.urlopen(request, context=context, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    tag = str(payload.get("tag_name", "")).strip()
    if not tag:
        raise RuntimeError("Failed to resolve latest llama.cpp tag from GitHub API")

    return tag


def build_llama_cpp_url(tag: str, target: str) -> str:
    target_meta = TARGETS.get(target)
    if not target_meta:
        raise ValueError(f"Unsupported target: {target}")

    normalized_tag = (tag or "").strip()
    if not normalized_tag or normalized_tag == "latest":
        normalized_tag = get_latest_llama_cpp_tag()

    archive_name = target_meta["archive_name_template"].format(tag=normalized_tag)
    return f"https://github.com/ggml-org/llama.cpp/releases/download/{normalized_tag}/{archive_name}"


def build_llama_cpp_extra_urls(tag: str, target: str) -> list[str]:
    target_meta = TARGETS.get(target)
    if not target_meta:
        raise ValueError(f"Unsupported target: {target}")

    normalized_tag = (tag or "").strip()
    if not normalized_tag or normalized_tag == "latest":
        normalized_tag = get_latest_llama_cpp_tag()

    templates = target_meta.get("extra_archive_name_templates", [])
    return [
        f"https://github.com/ggml-org/llama.cpp/releases/download/{normalized_tag}/{template.format(tag=normalized_tag)}"
        for template in templates
    ]


def _copy_tree_contents(source_dir: Path, destination_dir: Path):
    destination_dir.mkdir(parents=True, exist_ok=True)
    for item in source_dir.iterdir():
        target = destination_dir / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def _extract_archive_to_llama_dir(url: str, llama_path: Path, executable_name: str | None = None):
    with tempfile.TemporaryDirectory(prefix="llama-cpp-") as tmp:
        tmp_path = Path(tmp)
        lower_url = url.lower()
        if lower_url.endswith(".zip"):
            archive_path = tmp_path / "llama_archive.zip"
        elif lower_url.endswith(".tar.gz"):
            archive_path = tmp_path / "llama_archive.tar.gz"
        elif lower_url.endswith(".tgz"):
            archive_path = tmp_path / "llama_archive.tgz"
        else:
            raise ValueError(f"Unsupported archive URL: {url}")

        _download_file(url, archive_path)

        extract_dir = tmp_path / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        _extract_archive(archive_path, extract_dir)

        if executable_name:
            executable_paths = [p for p in extract_dir.rglob(executable_name) if p.is_file()]
            if not executable_paths:
                raise RuntimeError(f"Cannot find {executable_name} in archive: {url}")

            runtime_bin_dir = executable_paths[0].parent
            _copy_tree_contents(runtime_bin_dir, llama_path)
            return

        top_level_items = list(extract_dir.iterdir())
        root_files = [p for p in top_level_items if p.is_file()]
        root_dirs = [p for p in top_level_items if p.is_dir()]
        source_root = root_dirs[0] if len(root_dirs) == 1 and not root_files else extract_dir
        _copy_tree_contents(source_root, llama_path)


def prepare_llama_cpp_for_target(target: str, tag: str = "latest", llama_dir: str | Path = "llama") -> Path:
    target_meta = TARGETS.get(target)
    if not target_meta:
        raise ValueError(f"Unsupported target: {target}")

    url = build_llama_cpp_url(tag, target)
    extra_urls = build_llama_cpp_extra_urls(tag, target)
    executable_name = target_meta["executable"]
    output = prepare_llama_cpp(url, executable_name, llama_dir)
    llama_path = Path(llama_dir)
    for extra_url in extra_urls:
        _extract_archive_to_llama_dir(extra_url, llama_path, executable_name=None)
    return output


def _extract_archive(archive_path: Path, output_dir: Path):
    name = archive_path.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(output_dir)
        return

    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        with tarfile.open(archive_path, "r:gz") as tf:
            tf.extractall(output_dir)
        return

    raise ValueError(f"Unsupported archive format: {archive_path.name}")


def prepare_llama_cpp(url: str, executable_name: str, llama_dir: str | Path = "llama") -> Path:
    llama_path = Path(llama_dir)
    llama_path.mkdir(parents=True, exist_ok=True)

    _extract_archive_to_llama_dir(url, llama_path, executable_name)

    resolved_executable = llama_path / executable_name
    if not resolved_executable.exists():
        raise RuntimeError(f"Failed to stage {executable_name} to {resolved_executable}")

    return resolved_executable


def collect_llama_datas(llama_dir: str | Path = "llama") -> list[tuple[str, str]]:
    llama_path = Path(llama_dir)
    if not llama_path.exists():
        return []

    datas: list[tuple[str, str]] = []
    for file_path in llama_path.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() == ".gguf":
            continue

        relative_parent = file_path.relative_to(llama_path).parent
        destination = Path("llama") / relative_parent
        datas.append((str(file_path), destination.as_posix()))

    return datas


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and stage llama.cpp runtime files")
    parser.add_argument("--url", help="llama.cpp release archive URL")
    parser.add_argument("--executable", help="Executable name to search for")
    parser.add_argument("--target", choices=sorted(TARGETS.keys()), help="Predefined platform target")
    parser.add_argument("--tag", default="latest", help="llama.cpp release tag, default latest")
    parser.add_argument("--llama-dir", default="llama", help="Destination llama runtime directory")
    args = parser.parse_args()

    if args.target:
        output = prepare_llama_cpp_for_target(args.target, args.tag, args.llama_dir)
    else:
        if not args.url or not args.executable:
            parser.error("Either --target, or both --url and --executable, are required")
        output = prepare_llama_cpp(args.url, args.executable, args.llama_dir)

    print(f"Prepared llama.cpp runtime: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

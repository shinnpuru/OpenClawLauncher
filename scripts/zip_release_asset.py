import os
import sys
import zipfile
from pathlib import Path


def main() -> int:
    tag = os.environ.get("GITHUB_REF_NAME")
    platform = os.environ.get("MATRIX_PLATFORM")

    if not tag or not platform:
        print("Missing GITHUB_REF_NAME or MATRIX_PLATFORM", file=sys.stderr)
        return 1

    source_dir = Path("dist") / "openclaw-launcher"
    if not source_dir.is_dir():
        print(f"Source directory not found: {source_dir}", file=sys.stderr)
        return 1

    release_dir = Path("release")
    release_dir.mkdir(parents=True, exist_ok=True)

    zip_path = release_dir / f"openclaw-launcher-{tag}-{platform}.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to("dist"))

    print(f"Created: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

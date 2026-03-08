# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from scripts.prepare_llama_cpp import collect_llama_datas, prepare_llama_cpp_for_target

block_cipher = None

LLAMA_CPP_TAG = os.environ.get("LLAMA_CPP_TAG", "latest")
LLAMA_CPP_TARGET = os.environ.get("LLAMA_CPP_TARGET", "win-vulkan-x64")

prepare_llama_cpp_for_target(
    LLAMA_CPP_TARGET,
    tag=LLAMA_CPP_TAG,
)

datas = [
    ("src/openclaw_launcher/ui/i18n", "openclaw_launcher/ui/i18n"),
    ("logo.png", "."),
]

datas.extend(collect_llama_datas("llama"))

icon_file = "logo.ico" if sys.platform.startswith("win") else "logo.png"

a = Analysis(
    ["src/openclaw_launcher/main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="openclaw-launcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="openclaw-launcher",
)

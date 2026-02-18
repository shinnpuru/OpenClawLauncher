# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

datas = [
    ("src/openclaw_launcher/ui/i18n", "openclaw_launcher/ui/i18n"),
    ("logo.png", "."),
]

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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="openclaw-launcher",
)

app = BUNDLE(
    coll,
    name="openclaw-launcher.app",
    icon="logo.icns",
    bundle_identifier="com.openclaw.launcher",
)

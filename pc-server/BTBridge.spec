# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    "adb_manager",
    "audio_capture",
    "audio_control",
    "audioop",
    "dsp",
    "i18n",
    "protocol",
    "server",
    "tray",
    "ui",
]

for pkg in ("customtkinter", "pyaudiowpatch", "pystray"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

icon_file = os.path.join(SPECPATH, "btbridge.ico")
if os.path.isfile(icon_file):
    datas.append((icon_file, "."))

platform_tools_dir = os.path.abspath(
    os.path.join(SPECPATH, "..", ".tools", "android-sdk", "platform-tools")
)
for adb_bin in ("adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll"):
    full_path = os.path.join(platform_tools_dir, adb_bin)
    if os.path.isfile(full_path):
        binaries.append((full_path, "adb"))

a = Analysis(
    [os.path.join(SPECPATH, "main.py")],
    pathex=[SPECPATH],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BTBridge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file if os.path.isfile(icon_file) else None,
)

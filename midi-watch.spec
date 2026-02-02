# -*- mode: python ; coding: utf-8 -*-
import os
import shutil

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],  # Do NOT include config.yaml - it should be external
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='midi-watch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Copy root config.yaml to dist so the executable has a default config next to it
# DISTPATH is injected by PyInstaller and points to the dist folder (e.g. project/dist)
_spec_dir = os.path.dirname(DISTPATH)
_config_src = os.path.join(_spec_dir, 'config.yaml')
_config_dst = os.path.join(DISTPATH, 'config.yaml')
if os.path.exists(_config_src):
    shutil.copy2(_config_src, _config_dst)
    print(f"Copied config.yaml to {_config_dst}")
else:
    print(f"Warning: {_config_src} not found, skipping config copy")

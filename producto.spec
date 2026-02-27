# -*- mode: python ; coding: utf-8 -*-
"""
Producto v3.0 - PyInstaller Specification File

This file defines how PyInstaller should package Producto into a standalone executable.

To build:
    pyinstaller producto.spec

Output:
    dist/Producto.exe (Windows executable)
"""

block_cipher = None

a = Analysis(
    ['producto.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include assets if present
        # ('assets', 'assets'),
    ],
    hiddenimports=[
        # Explicit imports for modules that PyInstaller might miss
        'keyring.backends.Windows',
        'outlook_extractor_v2_config',
        'outlook_extractor_v2_integrations',
        'outlook_extractor_v2_monitoring',
        'meeting_classifier_v2',
        'meeting_prompts_v2',
        'win32com',
        'win32com.client',
        'pywintypes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary packages to reduce size
        'pytest',
        'black',
        'pylint',
        'IPython',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
    ],
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
    name='Producto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression (reduces size)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/producto.ico' if False else None,  # Set to True when icon exists
    version_file=None,  # Can add version info resource
)

# Alternative: One-folder mode (faster startup, more files)
# Uncomment below and comment out the EXE block above to use
"""
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Producto',
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
    icon='assets/producto.ico' if False else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Producto',
)
"""

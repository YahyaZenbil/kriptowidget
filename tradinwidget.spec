# PyInstaller spec — TradinWidget
# Calistir: build_exe.bat veya: pyinstaller tradinwidget.spec

import os
from pathlib import Path

PROJECT = Path(os.path.abspath(SPECPATH))

a = Analysis(
    [str(PROJECT / "main.py")],
    pathex=[str(PROJECT)],
    binaries=[],
    datas=[(str(PROJECT / "chart_template.html"), ".")],
    hiddenimports=["clr_loader", "pythonnet"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="TradinWidget",
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
)

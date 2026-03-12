# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for PickyText.

Build:
    pyinstaller pickytext.spec

Output: dist\PickyText\PickyText.exe  (one-folder mode for fast startup)
"""

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        # App assets (icon, etc.)
        ("assets", "assets"),
        # version.py must be importable at root level
        ("version.py", "."),
    ],
    hiddenimports=[
        # PyQt6
        "PyQt6.sip",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        # WinRT / winsdk
        "winsdk",
        "winsdk.windows.media.ocr",
        "winsdk.windows.graphics.imaging",
        "winsdk.windows.globalization",
        "winsdk.windows.storage.streams",
        "winsdk._winrt",
        # keyboard
        "keyboard",
        "keyboard._winkeyboard",
        # Pillow
        "PIL",
        "PIL._imaging",
        "PIL._webp",
        "PIL.Image",
        "PIL.ImageDraw",
        # httpx
        "httpx",
        "httpx._transports.default",
        "httpx._transports.asgi",
        # mss
        "mss",
        "mss.windows",
        # packaging
        "packaging",
        "packaging.version",
        # asyncio
        "asyncio",
        # Optional: argostranslate (bundled, models downloaded at runtime)
        "argostranslate",
        "argostranslate.package",
        "argostranslate.translate",
        "argostranslate.settings",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy test/dev packages
        "pytest",
        "sphinx",
        "docutils",
        "setuptools",
        "_pytest",
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
    [],
    exclude_binaries=True,
    name="PickyText",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets\\icon.ico",
    version_file=None,      # set to a version_info.txt if you want file properties
    uac_admin=False,        # keyboard hook works without admin on modern Windows
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PickyText",
)

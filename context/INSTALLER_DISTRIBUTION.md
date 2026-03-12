# PickyText — Installer, Distribution & Versioning

> **Status: 📋 Not yet started.** Python source + venv is the development setup.
> This file contains the planned production build pipeline.

## Why an Installer
- Professional Windows uninstall support (`Add or Remove Programs`)
- Registry entries (startup, app registration) done cleanly
- Optional components can be bundled or downloaded at install time
- Avoids SmartScreen false positives better than a raw `.exe`
- Generates a proper Start Menu entry and desktop shortcut (optional)

---

## Build Pipeline

```
Python source
    → PyInstaller → dist/PickyText/ (folder with .exe + deps)
        → Inno Setup → PickyText_Setup_v1.x.x.exe
            → GitHub Release asset
```

---

## PyInstaller Configuration (`pickytext.spec`)

```python
# Key settings
a = Analysis(
    ['main.py'],
    hiddenimports=['winrt.windows.media.ocr', 'winrt.windows.graphics.imaging'],
    excludes=['tkinter', 'matplotlib', 'scipy'],  # trim unused packages
)
exe = EXE(a, name='PickyText', icon='assets/icon.ico', console=False)
```

- `console=False`: no terminal window on launch
- UPX compression optional (reduces size ~30%, adds startup time ~50ms)
- Target size: < 80MB installed (without optional components)

---

## Inno Setup Script (`installer/pickytext.iss`)

### Structure

```
[Setup]
AppName=PickyText
AppVersion={version}
AppPublisher=Riccardo
DefaultDirName={autopf}\PickyText
DefaultGroupName=PickyText
OutputBaseFilename=PickyText_Setup_{version}
Compression=lzma2/ultra64
WizardStyle=modern
MinVersion=10.0.22000  ; Windows 11

[Tasks]
Name: desktopicon; Description: "Create desktop shortcut"; Flags: unchecked
Name: startupentry; Description: "Start PickyText with Windows"; Flags: unchecked

[Components]
Name: main; Description: "PickyText (required)"; Flags: fixed
Name: tesseract; Description: "Tesseract OCR (offline OCR support)"
Name: argos; Description: "Argos Translate (offline translation)"

[Files]
Source: "..\dist\PickyText\*"; DestDir: "{app}"; Flags: recursesubdirs
Source: "..\dist\PickyText\PickyText.exe"; DestDir: "{app}"

[Icons]
Name: "{group}\PickyText"; Filename: "{app}\PickyText.exe"
Name: "{commondesktop}\PickyText"; Filename: "{app}\PickyText.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "PickyText"; \
  ValueData: "{app}\PickyText.exe"; \
  Flags: uninsdeletevalue; Tasks: startupentry

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
```

### Optional Components
- **Tesseract**: Installer downloads Tesseract binary from official GitHub release + user-selected `.traineddata` language files
- **Argos Translate**: Installer runs `pip install argostranslate` into app's embedded Python, then prompts language pair selection

---

## Versioning

### Scheme
SemVer: `MAJOR.MINOR.PATCH`

| Bump | When |
|---|---|
| PATCH | Bug fixes, small tweaks |
| MINOR | New features, backward compatible |
| MAJOR | Breaking changes, major redesigns |

### Version File
Single source of truth: `pickytext/version.py`
```python
__version__ = "1.0.0"
```

Imported by `main.py`, embedded in installer via GitHub Actions, shown in tray menu and about dialog.

### Git Tags
```bash
git tag v1.0.1
git push origin v1.0.1
# → triggers GitHub Actions build
```

---

## GitHub Actions (`.github/workflows/release.yml`)

```yaml
name: Build & Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller
      
      - name: Extract version from tag
        id: version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT
        shell: bash
      
      - name: Build with PyInstaller
        run: pyinstaller pickytext.spec
      
      - name: Build installer with Inno Setup
        run: |
          choco install innosetup -y
          iscc /DAppVersion=${{ steps.version.outputs.VERSION }} installer/pickytext.iss
      
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: installer/Output/PickyText_Setup_*.exe
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Auto-Update (`core/updater.py`)

- Runs once at startup in background thread
- Calls `https://api.github.com/repos/[user]/PickyText/releases/latest`
- Compares `tag_name` (e.g. `v1.2.0`) against current `__version__`
- If newer: tray notification "PickyText v1.2.0 available — click to download"
- Click opens browser to GitHub Release page (no silent install, user decides)
- No background service, no scheduled task — just startup check

```python
def check_for_update(current_version: str) -> tuple[bool, str, str]:
    """Returns (has_update, latest_version, release_url)"""
    r = requests.get(
        "https://api.github.com/repos/[user]/PickyText/releases/latest",
        timeout=5,
        headers={"Accept": "application/vnd.github+json"}
    )
    latest = r.json()["tag_name"].lstrip("v")
    has_update = version.parse(latest) > version.parse(current_version)
    return has_update, latest, r.json()["html_url"]
```

Uses `packaging.version` for correct semver comparison.

---

## Signing (Future)
Currently unsigned. SmartScreen will warn on first run. For future distribution:
- Code signing certificate ($100–300/yr from Sectigo/DigiCert)
- Or use Windows Defender Application Control bypass via reputation building
- Note in README for first-time users to click "More info → Run anyway"

---

## Repository Structure

```
PickyText/
├── pickytext/          # Source code
├── installer/
│   ├── pickytext.iss   # Inno Setup script
│   └── Output/         # (gitignored) compiled installer
├── .github/
│   └── workflows/
│       └── release.yml
├── requirements.txt
├── pickytext.spec      # PyInstaller spec
├── README.md
├── CHANGELOG.md        # Updated per release
└── docs/               # MD context files (this folder)
```

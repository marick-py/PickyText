; ===============================================================
;  PickyText — Inno Setup installer script
;  Requires: Inno Setup 6.x  https://jrsoftware.org/isinfo.php
;
;  Build steps:
;    1. pyinstaller pickytext.spec           (creates dist\PickyText\)
;    2. Open this file in Inno Setup IDE → Build → Compile
;       OR:  iscc installer\pickytext.iss
;
;  Optional Tesseract component:
;    Download the UB-Mannheim 64-bit installer and save it as:
;      installer\tesseract-setup.exe
;    (https://github.com/UB-Mannheim/tesseract/wiki)
;    If the file is absent the Tesseract component is hidden automatically.
; ===============================================================

#define AppName      "PickyText"
#define AppVersion   "0.1.0"
#define AppPublisher "marick-py"
#define AppURL       "https://github.com/marick-py/PickyText"
#define AppExe       "PickyText.exe"
#define DistDir      "..\dist\PickyText"

[Setup]
AppId={{A7F3C2B1-5D4E-4F8A-9C3D-1E2F5A6B7C8D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases

; Install into per-user AppData by default (no UAC prompt required)
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes

; One installer file, no disk spanning
OutputDir=..\dist\installer
OutputBaseFilename=PickyText-{#AppVersion}-setup
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
InternalCompressLevel=ultra64

; Uninstaller
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}

; Minimum Windows version: Windows 10 (WinRT OCR requirement)
MinVersion=10.0.17763

; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Wizard style
WizardStyle=modern
WizardSmallImageFile=..\assets\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; ---------------------------------------------------------------
;  Optional components
; ---------------------------------------------------------------
[Types]
Name: "full";    Description: "Full installation"
Name: "compact"; Description: "Compact installation (no offline translation)"
Name: "custom";  Description: "Custom installation"; Flags: iscustom

[Components]
; Core — always required
Name: "core";    Description: "{#AppName} application (required)";  Types: full compact custom; Flags: fixed

; Argos Translate — bundled Python package (no extra download at install time;
; language model pairs are downloaded inside the app via Settings → Optional Features)
Name: "argos";   Description: "Argos Translate — offline translation fallback (~15 MB)"; Types: full

; Tesseract OCR — only shown if the setup file is present next to this script
#if FileExists("tesseract-setup.exe")
Name: "tessocr"; Description: "Tesseract OCR — alternative OCR engine"; Types: full
#endif

; ---------------------------------------------------------------
;  Files
; ---------------------------------------------------------------
[Files]
; Core app — everything PyInstaller produced
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core

; Argos marker file so the app knows it was installed
; (argostranslate is already bundled inside the PyInstaller output — this
;  component simply controls whether those files are copied)
; If you want to make argostranslate truly optional (smaller download), build
; two separate PyInstaller outputs and reference the right one per component.

#if FileExists("tesseract-setup.exe")
; Tesseract installer — extracted to a temp location then run
Source: "tesseract-setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Components: tessocr
#endif

; ---------------------------------------------------------------
;  Run after install
; ---------------------------------------------------------------
[Run]
#if FileExists("tesseract-setup.exe")
; Run the Tesseract installer silently (it adds itself to PATH)
Filename: "{tmp}\tesseract-setup.exe"; Parameters: "/S"; \
  StatusMsg: "Installing Tesseract OCR…"; \
  Components: tessocr; Flags: waituntilterminated

; After Tesseract installs, let the user know to set the path in Settings
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; \
  Flags: nowait postinstall skipifsilent; Components: core
#else
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; \
  Flags: nowait postinstall skipifsilent; Components: core
#endif

; ---------------------------------------------------------------
;  Shortcuts
; ---------------------------------------------------------------
[Icons]
; Start Menu
Name: "{group}\{#AppName}";         Filename: "{app}\{#AppExe}"; IconFilename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

; Desktop shortcut (optional — user can deselect in wizard)
Name: "{autodesktop}\{#AppName}";   Filename: "{app}\{#AppExe}"; IconFilename: "{app}\{#AppExe}"; \
  Tasks: desktopicon

; ---------------------------------------------------------------
;  Tasks
; ---------------------------------------------------------------
[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

; ---------------------------------------------------------------
;  Registry — startup (mirrors what the app sets itself)
; ---------------------------------------------------------------
; The app manages this via Settings → "Start with Windows", so we don't
; add it here. Keeping this section for reference only.

; ---------------------------------------------------------------
;  Uninstall — clean up app data on uninstall (optional prompt)
; ---------------------------------------------------------------
[Code]
var
  CleanDataPage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  // Ask whether to delete app data on uninstall (only shown during uninstall)
end;

function InitializeUninstall(): Boolean;
var
  res: Integer;
begin
  Result := True;
  res := MsgBox(
    'Do you want to also delete saved settings and history?' + #13#10 +
    '(Stored in %APPDATA%\PickyText)',
    mbConfirmation, MB_YESNO
  );
  if res = IDYES then
  begin
    DelTree(ExpandConstant('{userappdata}\PickyText'), True, True, True);
  end;
end;

; Inno Setup script for the ELM11 IDE Windows installer.
;
; Prerequisites (on Windows):
;   1. Python 3.10+ installed.
;   2. `pip install pyinstaller PyQt6 pyserial`
;   3. Inno Setup 6 — https://jrsoftware.org/isdl.php
;   4. An elm11-ide.ico file next to this .iss (use an online PNG→ICO
;      converter or ImageMagick:  magick elm11-ide.png -define icon:auto-resize elm11-ide.ico)
;
; Build:
;   cd <repo root>
;   pyinstaller --clean --noconfirm packaging\elm11-ide.spec
;   ISCC.exe packaging\elm11-ide.iss
;
; Output:
;   dist\ELM11_IDE_Setup_<version>.exe

#define MyAppName       "ELM11 IDE"
#define MyAppVersion    "0.1.0"
#define MyAppPublisher  "BrisbaneSilicon"
#define MyAppURL        "https://brisbanesilicon.com.au"
#define MyAppExeName    "elm11-ide.exe"
#define SrcDir          "..\dist\elm11-ide"
#define OutputBase      "ELM11_IDE_Setup_" + MyAppVersion

[Setup]
AppId={{7B6E4A9C-2D1F-4A5E-9B2A-ELM11-IDE-0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\ELM11 IDE
DefaultGroupName=ELM11 IDE
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
Compression=lzma2/ultra
SolidCompression=yes
OutputDir=..\dist
OutputBaseFilename={#OutputBase}
SetupIconFile=elm11-ide.ico
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SrcDir}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}";     Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

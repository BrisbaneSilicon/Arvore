; Inno Setup script for the Arvore Windows installer.
;
; Prerequisites (on Windows):
;   1. Python 3.10+ installed.
;   2. `pip install pyinstaller PyQt6 pyserial`
;   3. Inno Setup 6 — https://jrsoftware.org/isdl.php
;   4. An arvore.ico file next to this .iss (use an online PNG→ICO
;      converter or ImageMagick:  magick arvore.png -define icon:auto-resize arvore.ico)
;
; Build:
;   cd <repo root>
;   pyinstaller --clean --noconfirm packaging\arvore.spec
;   ISCC.exe packaging\arvore.iss
;
; Output:
;   dist\Arvore_Setup_<version>.exe

#define MyAppName       "Arvore"
#define MyAppVersion    "0.1.0"
#define MyAppPublisher  "BrisbaneSilicon"
#define MyAppURL        "https://brisbanesilicon.com.au"
#define MyAppExeName    "arvore.exe"
#define SrcDir          "..\dist\arvore"
#define OutputBase      "Arvore_Setup_" + MyAppVersion

[Setup]
AppId={{B5E1B2A7-4C3D-4E9F-A1D6-7F2C9E0B3A84}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\Arvore
DefaultGroupName=Arvore
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
SetupIconFile=arvore.ico
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

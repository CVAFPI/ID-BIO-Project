#define AppName "CVAFPI Identification System"
#define AppVersion "2.1.1"
#define AppPublisher "Christian Vision Academy Pampanga Foundation Inc."
#define AppURL "https://github.com/CVAFPI/ID-BIO-Project"

[Setup]
AppId={{B1A9276D-9F26-4D25-936B-2078A25130E2}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
AppCopyright=Copyright (C) 2026 {#AppPublisher}
AppComments=CSV-based student identification and attendance kiosk.
AppReadmeFile={app}\README.md
DefaultDirName={localappdata}\Programs\CVAFPI-IDSYS
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
LicenseFile=dist\LICENSE
SetupIconFile=dist\CVAIDSYSLOGO.ico
OutputDir=installer
OutputBaseFilename=CVAFPI-IDSYS-Setup
SetupLogging=yes
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=2.1.1.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
UninstallDisplayIcon={app}\CVAFPI-IDSYS.exe

[Messages]
ConfirmUninstall=Do you want to uninstall {#AppName}? Your CSV records, settings, attendance logs, and snapshots will remain in %LOCALAPPDATA%\CVAFPI-IDSYS.

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\CVAFPI-IDSYS.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\data.csv"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\backup-data.csv"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\settings.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\LICENSES\*"; DestDir: "{app}\Licenses"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}\{#AppName}"; Filename: "{app}\CVAFPI-IDSYS.exe"; WorkingDir: "{app}"
Name: "{autoprograms}\{#AppName}\Documentation\README"; Filename: "{app}\README.md"
Name: "{autoprograms}\{#AppName}\Licenses\All licenses and credits"; Filename: "{app}\Licenses\ALL-LICENSES.txt"
Name: "{autoprograms}\{#AppName}\Licenses\Credits"; Filename: "{app}\Licenses\CREDITS.txt"
Name: "{autoprograms}\{#AppName}\Licenses\Project license"; Filename: "{app}\LICENSE"
Name: "{autoprograms}\{#AppName}\Licenses\Python Software Foundation License"; Filename: "{app}\Licenses\Python-PSF-2.0.txt"
Name: "{autoprograms}\{#AppName}\Licenses\JsBarcode MIT License"; Filename: "{app}\Licenses\jsbarcode_MIT_LICENSE.txt"
Name: "{autoprograms}\{#AppName}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\CVAFPI-IDSYS.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\CVAFPI-IDSYS.exe"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent

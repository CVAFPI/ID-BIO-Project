#define MyAppName "CVAFPI Identification System"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Lance@Debian13"
#define MyAppRepo "https://github.com/CVAFPI/ID-BIO-Project/tree/SQL-IDBIOSYS-VERWIN"

[Setup]
AppId={{A6D45B13-7F22-4F1A-A4F1-42E0743F83C1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/CVAFPI
AppSupportURL={#MyAppRepo}
AppUpdatesURL={#MyAppRepo}
DefaultDirName={autopf}\CVAFPI Identification System
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
LicenseFile=LICENSES\ALL-LICENSES.txt
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\CVAFPI-IDSYS.exe
OutputDir=installer-output
OutputBaseFilename=CVAFPI-IDSYS-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
SetupIconFile=CVAIDSYSLOGO.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Dirs]
; The launcher stores its Edge kiosk profile beside the executable.
; Grant standard users access to this profile directory, not the whole install.
Name: "{app}\.kiosk-profile"; Permissions: users-modify

[Files]
Source: "dist\CVAFPI-IDSYS.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "CVAIDSYSLOGO.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "Launch-CVAFPI.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}\Licenses"; DestName: "PROJECT-LICENSE.txt"; Flags: ignoreversion
Source: "LICENSES\*.txt"; DestDir: "{app}\Licenses"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}\Documentation"; Flags: ignoreversion
Source: "ARCHITECTURE.md"; DestDir: "{app}\Documentation"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\Launch-CVAFPI.bat"; WorkingDir: "{app}"; IconFilename: "{app}\CVAFPI-IDSYS.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Launch-CVAFPI.bat"; WorkingDir: "{app}"; IconFilename: "{app}\CVAFPI-IDSYS.exe"; Tasks: desktopicon
Name: "{group}\Licenses\All Licenses and Credits"; Filename: "{app}\Licenses\ALL-LICENSES.txt"
Name: "{group}\Licenses\Project License"; Filename: "{app}\Licenses\PROJECT-LICENSE.txt"
Name: "{group}\Licenses\JsBarcode MIT License"; Filename: "{app}\Licenses\jsbarcode_MIT_LICENSE.txt"
Name: "{group}\Licenses\Python PSF 2.0"; Filename: "{app}\Licenses\Python-PSF-2.0.txt"
Name: "{group}\Licenses\Project Credits"; Filename: "{app}\Licenses\CREDITS.txt"
Name: "{group}\Documentation\Readme"; Filename: "{app}\Documentation\README.md"
Name: "{group}\Documentation\Architecture"; Filename: "{app}\Documentation\ARCHITECTURE.md"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\Launch-CVAFPI.bat"; Description: "Launch {#MyAppName}"; Flags: postinstall shellexec nowait skipifsilent runasoriginaluser

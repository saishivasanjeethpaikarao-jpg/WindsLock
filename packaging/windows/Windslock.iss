#define MyAppName "Windslock"
#if GetEnv("WINDSLOCK_VERSION") == ""
#define MyAppVersion "0.1.0"
#else
#define MyAppVersion GetEnv("WINDSLOCK_VERSION")
#endif
#define MyAppPublisher "Windslock"
#define MyAppExeName "Windslock.exe"

[Setup]
AppId={{8F3C727D-47F9-4D8F-A9EA-4E1F6B8A334D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Windslock
DefaultGroupName=Windslock
DisableProgramGroupPage=yes
OutputDir=..\..\dist\installer
OutputBaseFilename=Windslock-Setup
SetupIconFile=..\..\assets\windslock.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\..\dist\Windslock\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Windslock"; Filename: "{app}\Windslock.exe"
Name: "{group}\Windslock Tray"; Filename: "{app}\WindslockTray\WindslockTray.exe"
Name: "{group}\Windslock Proxy"; Filename: "{app}\WindslockProxy\WindslockProxy.exe"
Name: "{group}\Install Start With Windows"; Filename: "{app}\install_startup_task.bat"
Name: "{group}\Uninstall Start With Windows"; Filename: "{app}\uninstall_startup_task.bat"
Name: "{autodesktop}\Windslock"; Filename: "{app}\Windslock.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Windslock.exe"; Description: "Launch Windslock"; Flags: nowait postinstall skipifsilent

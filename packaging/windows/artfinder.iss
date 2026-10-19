; Per-user installation. User data stays in %LOCALAPPDATA%\ArtFinder.
#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#ifndef AppExecutable
  #define AppExecutable SourcePath + "\..\..\dist\review\ArtFinder.exe"
#endif
#ifndef AppIdentity
  #define AppIdentity "{{8BCB6BB4-A439-4592-98B7-1C7218CC3A25}"
#endif
#ifndef AppDisplayName
  #define AppDisplayName "ArtFinder"
#endif

[Setup]
AppId={#AppIdentity}
AppName={#AppDisplayName}
AppVersion={#AppVersion}
AppPublisher=ArtFinder contributors
DefaultDirName={localappdata}\Programs\ArtFinder
DefaultGroupName=ArtFinder
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist\review
OutputBaseFilename=ArtFinder-Setup-{#AppVersion}
SetupIconFile=..\..\assets\artfinder.ico
UninstallDisplayIcon={app}\ArtFinder.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes
CloseApplicationsFilter=ArtFinder.exe
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "{#AppExecutable}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ArtFinder"; Filename: "{app}\ArtFinder.exe"
Name: "{autodesktop}\ArtFinder"; Filename: "{app}\ArtFinder.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ArtFinder.exe"; Description: "{cm:LaunchProgram,ArtFinder}"; Flags: nowait postinstall skipifsilent

; Deliberately no UninstallDelete: downloads, tags and vault survive uninstall.

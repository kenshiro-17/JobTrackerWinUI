; ----------------------------------------------------------------------
; JobTracker – Inno Setup installer
; ----------------------------------------------------------------------
; This script creates a single EXE installer that detects the OS architecture
; and installs the appropriate self‑contained WinUI 3 build (x64 or x86).
; ----------------------------------------------------------------------
[Setup]
AppName=JobTracker
AppVersion=1.0.0
; Install to user's local AppData\Programs (Standard for per-user installs)
DefaultDirName={autopf}\JobTracker
DefaultGroupName=JobTracker
OutputBaseFilename=JobTrackerInstaller
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x86 x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\JobTracker.exe
; Run as the current user (fixes the UserAppData warning and ensures correct data migration)
PrivilegesRequired=lowest

[Dirs]
Name: "{userappdata}\JobTracker"

[Code]
function QTDataExists: Boolean;
begin
  Result := FileExists(ExpandConstant('{userappdata}\Rahul Raj\Job Tracker\jobs.json'));
end;

[Files]
; 64‑bit build – installed only on a 64‑bit OS
Source: "Distribution\JobTracker_x64\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion; Check: IsWin64
; 32‑bit build – installed only on a 32‑bit OS
Source: "Distribution\JobTracker_x86\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion; Check: not IsWin64
; (optional) include the README for reference
Source: "Distribution\README.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\JobTracker"; Filename: "{app}\JobTracker.exe"; WorkingDir: "{app}"
; Uncomment the next line if you also want a desktop shortcut
; Name: "{commondesktop}\JobTracker"; Filename: "{app}\JobTracker.exe"; WorkingDir: "{app}"

[Run]
; Migrate old QT data if it exists (Source: Rahul Raj\Job Tracker -> Dest: JobTracker)
Filename: "cmd"; Parameters: "/c copy ""{userappdata}\Rahul Raj\Job Tracker\jobs.json"" ""{userappdata}\JobTracker\jobs.json"" /Y"; Flags: runhidden waituntilterminated; Check: QTDataExists

; Launch the new app after install (unless silent)
Filename: "{app}\JobTracker.exe"; Description: "Launch JobTracker"; Flags: nowait postinstall skipifsilent

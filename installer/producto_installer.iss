; Producto v3.0 - Inno Setup Installer Script
; Creates a Windows installer for Producto

#define MyAppName "Producto"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "Cisco Systems"
#define MyAppURL "https://www.cisco.com/"
#define MyAppExeName "Producto.exe"
#define MyAppContact "qschalle@cisco.com"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{8D5E9C3B-4F7A-4B2E-9D3C-1E8F5A6B2C4D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; LicenseFile=..\docs\LICENSE.txt
; InfoBeforeFile=..\docs\README.md
OutputDir=Output
OutputBaseFilename=ProductoInstaller_v{#MyAppVersion}
; SetupIconFile=..\assets\producto.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} - Meeting Intelligence Assistant
VersionInfoCopyright=Copyright (C) 2025 {#MyAppPublisher}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode
Name: "startupicon"; Description: "Launch {#MyAppName} at Windows startup"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main executable (from PyInstaller build)
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Assets (if present - commented out for now, folder is empty)
; Source: "..\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists('..\assets')
; Documentation
Source: "..\docs\README.md"; DestDir: "{app}\docs"; Flags: ignoreversion
; Source: "..\docs\QUICKSTART.md"; DestDir: "{app}\docs"; Flags: ignoreversion isreadme; Check: FileExists('..\docs\QUICKSTART.md')
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{group}\Documentation"; Filename: "{app}\docs\README.md"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Registry]
; Create application registry keys
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; Flags: uninsdeletekeyifempty
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Contact"; ValueData: "{#MyAppContact}"

; Optional: Add shared organization credentials via registry (set by Group Policy instead)
; Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}\SharedConfig"; ValueType: string; ValueName: "ChatAI_ClientID"; ValueData: ""
; Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}\SharedConfig"; ValueType: string; ValueName: "ChatAI_ClientSecret"; ValueData: ""
; Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}\SharedConfig"; ValueType: string; ValueName: "WebexBotToken"; ValueData: ""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up application data on uninstall (optional, user may want to keep config)
; Type: filesandordirs; Name: "{userappdata}\Producto"

[Code]
var
  OutlookCheckPage: TOutputMsgWizardPage;
  
procedure InitializeWizard;
begin
  { Create custom page to check for Outlook }
  OutlookCheckPage := CreateOutputMsgPage(wpWelcome,
    'Prerequisites Check', 
    'Checking system requirements...',
    'Producto requires Microsoft Outlook to be installed on this computer. ' +
    'The installer will check if Outlook is available.');
end;

function IsOutlookInstalled: Boolean;
var
  OutlookPath: String;
begin
  { Check if Outlook is installed by looking for registry key }
  Result := RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\OUTLOOK.EXE',
    '', OutlookPath);
    
  { Also check 32-bit registry on 64-bit Windows }
  if not Result then
    Result := RegQueryStringValue(HKEY_LOCAL_MACHINE,
      'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\OUTLOOK.EXE',
      '', OutlookPath);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  
  { Check for Outlook when leaving the welcome page }
  if CurPageID = wpWelcome then
  begin
    if not IsOutlookInstalled then
    begin
      if MsgBox('Microsoft Outlook was not detected on this computer. ' +
                'Producto requires Outlook to function properly.' + #13#10#13#10 +
                'Do you want to continue with the installation anyway?',
                mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
      end;
    end
    else
    begin
      MsgBox('Microsoft Outlook detected. Installation can proceed.',
             mbInformation, MB_OK);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    { Post-installation tasks }
    { Could set up additional configurations here }
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  if MsgBox('Do you want to keep your Producto settings and credentials?', 
            mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
  begin
    { Don't delete user data }
  end
  else
  begin
    { User wants to remove everything }
    { This could delete %APPDATA%\Producto if we wanted }
  end;
end;

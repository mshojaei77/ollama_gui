#define MyAppName "Ollama Chatbot"
#define MyAppVersion "0.2"
#define MyAppPublisher "Shojaei"
#define MyAppURL "https://github.com/mshojaei77/ollama_gui"
#define MyAppExeName "app.exe"

[Setup]
AppId={{599935BA-A515-448D-AD9E-39A505E7C10E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=OllamaChatbot_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile=E:\ollama_gui\ollama.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Ollama Chatbot Installer
VersionInfoCopyright=© 2024 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "E:\ollama_gui\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "E:\ollama_gui\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  OllamaCheckPage: TOutputMsgWizardPage;

procedure CreateOllamaCheckPage();
begin
  OllamaCheckPage := CreateOutputMsgPage(wpWelcome,
    'Checking Ollama Installation', 'Verifying Ollama is installed on your system',
    'Please wait while Setup checks if Ollama is installed on your system. ' +
    'Ollama is required for this application to function properly.');
end;

function CheckOllama(): Boolean;
var
  ResultCode: Integer;
begin
  OllamaCheckPage.Description := 'Checking for Ollama...';
  if not Exec(ExpandConstant('{cmd}'), '/C ollama list', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    OllamaCheckPage.Description := 'Ollama is not installed or not in PATH. Please install Ollama before continuing.';
    Result := False;
  end
  else
  begin
    OllamaCheckPage.Description := 'Ollama is installed and accessible.';
    Result := True;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpReady then
  begin
    CreateOllamaCheckPage();
    if not CheckOllama() then
    begin
      if MsgBox('Ollama is not detected. Do you want to continue anyway?', mbConfirmation, MB_YESNO) = IDNO then
        WizardForm.Close;
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    if MsgBox(ExpandConstant('{cm:UninstallQuestion,{#MyAppName}}'), mbConfirmation, MB_YESNO) = IDNO then
      Abort;
  end;
end;
[Setup]
AppId={{B7B74800-9D3A-4E81-A6F2-87B21D6E0001}
AppName=BTBridge
AppVersion=1.0.0
AppPublisher=BTBridge
DefaultDirName={localappdata}\Programs\BTBridge
DefaultGroupName=BTBridge
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
SetupIconFile=..\pc-server\btbridge.ico
UninstallDisplayIcon={app}\BTBridge.exe
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir=..
OutputBaseFilename=BTBridge_Setup
CloseApplications=yes
RestartApplications=no
InfoBeforeFile=KURULUM_BILGISI.txt

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstünde kısayol oluştur"; GroupDescription: "Ek seçenekler:"
Name: "startup"; Description: "Windows başlangıcında BTBridge'i otomatik başlat"; GroupDescription: "Ek seçenekler:"; Flags: unchecked

[Files]
Source: "..\BTBridge.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\BTBridge.apk"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\.tools\android-sdk\platform-tools\adb.exe"; DestDir: "{app}\platform-tools"; Flags: ignoreversion
Source: "..\.tools\android-sdk\platform-tools\AdbWinApi.dll"; DestDir: "{app}\platform-tools"; Flags: ignoreversion
Source: "..\.tools\android-sdk\platform-tools\AdbWinUsbApi.dll"; DestDir: "{app}\platform-tools"; Flags: ignoreversion
Source: "KURULUM_BILGISI.txt"; DestDir: "{app}"; DestName: "Kullanim_Kilavuzu.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\BTBridge"; Filename: "{app}\BTBridge.exe"
Name: "{group}\Kullanım Kılavuzu"; Filename: "{app}\Kullanim_Kilavuzu.txt"
Name: "{group}\BTBridge'i Kaldır"; Filename: "{uninstallexe}"
Name: "{autodesktop}\BTBridge"; Filename: "{app}\BTBridge.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "BTBridge"; ValueData: """{app}\BTBridge.exe"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\BTBridge.exe"; Description: "BTBridge'i şimdi başlat"; Flags: nowait postinstall skipifsilent
Filename: "{app}\platform-tools\adb.exe"; Parameters: "install -r ""{app}\BTBridge.apk"""; Description: "Bağlı Android telefona BTBridge.apk kur (USB)"; Flags: postinstall skipifsilent unchecked runhidden

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM BTBridge.exe"; Flags: runhidden; RunOnceId: "StopBTBridge"
Filename: "{app}\platform-tools\adb.exe"; Parameters: "kill-server"; Flags: runhidden; RunOnceId: "StopAdbServer"

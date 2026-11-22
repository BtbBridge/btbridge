[Setup]
AppId={{B7B74800-9D3A-4E81-A6F2-87B21D6E0001}
AppName=BTBridge
AppVersion=1.1.0
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
LicenseFile=..\LICENSE
ShowLanguageDialog=yes
UsePreviousLanguage=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"; InfoBeforeFile: "KURULUM_BILGISI.txt"
Name: "english"; MessagesFile: "compiler:Default.isl"; InfoBeforeFile: "INSTALL_INFO_EN.txt"

[CustomMessages]
turkish.TaskDesktopIcon=Masaüstünde kısayol oluştur
turkish.TaskStartup=Windows başlangıcında BTBridge'i otomatik başlat
turkish.GroupExtra=Ek seçenekler:
turkish.IconUserGuide=Kullanım Kılavuzu
turkish.IconUninstall=BTBridge'i Kaldır
turkish.RunLaunchNow=BTBridge'i şimdi başlat
turkish.RunInstallApk=Bağlı Android telefona BTBridge.apk kur (USB)
english.TaskDesktopIcon=Create a desktop shortcut
english.TaskStartup=Launch BTBridge automatically at Windows startup
english.GroupExtra=Additional options:
english.IconUserGuide=User Guide
english.IconUninstall=Uninstall BTBridge
english.RunLaunchNow=Launch BTBridge now
english.RunInstallApk=Install BTBridge.apk to connected Android phone (USB)

[Tasks]
Name: "desktopicon"; Description: "{cm:TaskDesktopIcon}"; GroupDescription: "{cm:GroupExtra}"
Name: "startup"; Description: "{cm:TaskStartup}"; GroupDescription: "{cm:GroupExtra}"; Flags: unchecked

[Files]
Source: "..\BTBridge.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\BTBridge.apk"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\.tools\android-sdk\platform-tools\adb.exe"; DestDir: "{app}\platform-tools"; Flags: ignoreversion
Source: "..\.tools\android-sdk\platform-tools\AdbWinApi.dll"; DestDir: "{app}\platform-tools"; Flags: ignoreversion
Source: "..\.tools\android-sdk\platform-tools\AdbWinUsbApi.dll"; DestDir: "{app}\platform-tools"; Flags: ignoreversion
Source: "KURULUM_BILGISI.txt"; DestDir: "{app}"; DestName: "Kullanim_Kilavuzu.txt"; Languages: turkish; Flags: ignoreversion
Source: "INSTALL_INFO_EN.txt"; DestDir: "{app}"; DestName: "User_Guide.txt"; Languages: english; Flags: ignoreversion

[Icons]
Name: "{group}\BTBridge"; Filename: "{app}\BTBridge.exe"
Name: "{group}\{cm:IconUserGuide}"; Filename: "{app}\Kullanim_Kilavuzu.txt"; Languages: turkish
Name: "{group}\{cm:IconUserGuide}"; Filename: "{app}\User_Guide.txt"; Languages: english
Name: "{group}\{cm:IconUninstall}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\BTBridge"; Filename: "{app}\BTBridge.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "BTBridge"; ValueData: """{app}\BTBridge.exe"""; Flags: uninsdeletevalue; Tasks: startup
Root: HKCU; Subkey: "Software\BTBridge"; ValueType: string; ValueName: "Language"; ValueData: "tr"; Languages: turkish; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\BTBridge"; ValueType: string; ValueName: "Language"; ValueData: "en"; Languages: english; Flags: uninsdeletekey

[Run]
Filename: "{app}\BTBridge.exe"; Description: "{cm:RunLaunchNow}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\platform-tools\adb.exe"; Parameters: "install -r ""{app}\BTBridge.apk"""; Description: "{cm:RunInstallApk}"; Flags: postinstall skipifsilent unchecked runhidden

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM BTBridge.exe"; Flags: runhidden; RunOnceId: "StopBTBridge"
Filename: "{app}\platform-tools\adb.exe"; Parameters: "kill-server"; Flags: runhidden; RunOnceId: "StopAdbServer"

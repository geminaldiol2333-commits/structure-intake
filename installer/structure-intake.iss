; 结构式提取 — per-user installer. Optional desktop, Start menu, and file context menu.

#define AppName "结构式提取"
#define AppVersion "0.1.0"
#define AppExe "打开.vbs"

[Setup]
AppId={{7E4B9A2C-1D58-4F0E-9C3A-6B8E2F1A0D44}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL=https://github.com/geminaldiol2333-commits/structure-intake
DefaultDirName={localappdata}\StructureIntake
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=output
OutputBaseFilename=StructureIntake-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
InfoBeforeFile=使用前.txt
UninstallDisplayIcon={sys}\wscript.exe

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加项目:"
Name: "startmenu"; Description: "创建开始菜单快捷方式"; GroupDescription: "附加项目:"
Name: "contextmenu"; Description: "右键菜单：用结构式提取打开 PDF 和图片"; GroupDescription: "附加项目:"

[Files]
Source: "..\scratch\intake-v0.1\app.py"; DestDir: "{app}\scratch\intake-v0.1"
Source: "..\scratch\intake-v0.1\boxes.py"; DestDir: "{app}\scratch\intake-v0.1"
Source: "..\scratch\intake-v0.1\index.html"; DestDir: "{app}\scratch\intake-v0.1"
Source: "..\scratch\intake-v0.1\打开.vbs"; DestDir: "{app}\scratch\intake-v0.1"
Source: "..\scratch\intake-prototypes\prototype.py"; DestDir: "{app}\scratch\intake-prototypes"
Source: "..\requirements.txt"; DestDir: "{app}"
Source: "准备依赖.ps1"; DestDir: "{app}\installer"
Source: "使用前.txt"; DestDir: "{app}"; Flags: isreadme

[Icons]
Name: "{autodesktop}\{#AppName}"; Filename: "{sys}\wscript.exe"; Parameters: "//nologo ""{app}\scratch\intake-v0.1\{#AppExe}"""; WorkingDir: "{app}\scratch\intake-v0.1"; Tasks: desktopicon
Name: "{autoprograms}\{#AppName}"; Filename: "{sys}\wscript.exe"; Parameters: "//nologo ""{app}\scratch\intake-v0.1\{#AppExe}"""; WorkingDir: "{app}\scratch\intake-v0.1"; Tasks: startmenu
Name: "{autoprograms}\{#AppName}\重新准备依赖"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\准备依赖.ps1"""; Tasks: startmenu

[Registry]
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\StructureIntake"; ValueType: string; ValueName: ""; ValueData: "用结构式提取打开"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\StructureIntake\command"; ValueType: string; ValueName: ""; ValueData: "wscript.exe //nologo ""{app}\scratch\intake-v0.1\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\StructureIntake"; ValueType: string; ValueName: ""; ValueData: "用结构式提取打开"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\StructureIntake\command"; ValueType: string; ValueName: ""; ValueData: "wscript.exe //nologo ""{app}\scratch\intake-v0.1\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\StructureIntake"; ValueType: string; ValueName: ""; ValueData: "用结构式提取打开"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\StructureIntake\command"; ValueType: string; ValueName: ""; ValueData: "wscript.exe //nologo ""{app}\scratch\intake-v0.1\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\StructureIntake"; ValueType: string; ValueName: ""; ValueData: "用结构式提取打开"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\StructureIntake\command"; ValueType: string; ValueName: ""; ValueData: "wscript.exe //nologo ""{app}\scratch\intake-v0.1\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\StructureIntake"; ValueType: string; ValueName: ""; ValueData: "用结构式提取打开"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\StructureIntake\command"; ValueType: string; ValueName: ""; ValueData: "wscript.exe //nologo ""{app}\scratch\intake-v0.1\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\StructureIntake"; ValueType: string; ValueName: ""; ValueData: "用结构式提取打开"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\StructureIntake\command"; ValueType: string; ValueName: ""; ValueData: "wscript.exe //nologo ""{app}\scratch\intake-v0.1\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\StructureIntake"; ValueType: string; ValueName: ""; ValueData: "用结构式提取打开"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\StructureIntake\command"; ValueType: string; ValueName: ""; ValueData: "wscript.exe //nologo ""{app}\scratch\intake-v0.1\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\StructureIntake"; ValueType: string; ValueName: ""; ValueData: "用结构式提取打开"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\StructureIntake\command"; ValueType: string; ValueName: ""; ValueData: "wscript.exe //nologo ""{app}\scratch\intake-v0.1\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\StructureIntake"; ValueType: string; ValueName: ""; ValueData: "用结构式提取打开"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\StructureIntake\command"; ValueType: string; ValueName: ""; ValueData: "wscript.exe //nologo ""{app}\scratch\intake-v0.1\{#AppExe}"" ""%1"""; Tasks: contextmenu

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\准备依赖.ps1"""; StatusMsg: "正在准备 Python、识别库和模型..."; Flags: waituntilterminated

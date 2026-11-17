Set shell = CreateObject("Wscript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = folder
exe = "C:\Python314\pythonw.exe"
script = folder & "\app.py"
If Not files.FileExists(exe) Then
  MsgBox "pythonw missing"
  WScript.Quit 1
End If
shell.Run """" & exe & """ """ & script & """", 0, False

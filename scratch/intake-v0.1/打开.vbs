Set shell = CreateObject("Wscript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = folder
script = folder & "\app.py"

Function PythonExe()
  Dim marker, exe, localPy, versions, i, candidate
  marker = folder & "\pythonw.path"
  If files.FileExists(marker) Then
    exe = Trim(files.OpenTextFile(marker, 1).ReadAll)
    If files.FileExists(exe) Then
      PythonExe = exe
      Exit Function
    End If
  End If
  localPy = shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\"
  versions = Array("Python314", "Python313", "Python312")
  For i = 0 To UBound(versions)
    candidate = localPy & versions(i) & "\pythonw.exe"
    If files.FileExists(candidate) Then
      PythonExe = candidate
      Exit Function
    End If
  Next
  If files.FileExists("C:\Python314\pythonw.exe") Then
    PythonExe = "C:\Python314\pythonw.exe"
    Exit Function
  End If
  PythonExe = ""
End Function

exe = PythonExe()
If exe = "" Then
  MsgBox "没有找到 Python。请重新运行结构式提取的安装程序。", 48, "结构式提取"
  WScript.Quit 1
End If
If Not files.FileExists(script) Then
  MsgBox "找不到主程序。", 48, "结构式提取"
  WScript.Quit 1
End If

quoted = ""
For i = 0 To WScript.Arguments.Count - 1
  quoted = quoted & " """ & Replace(WScript.Arguments(i), """", """""") & """"
Next
shell.Run """" & exe & """ """ & script & """" & quoted, 0, False

' Launch CNexus gateway with no console window. Logs go to gateway.log.
Option Explicit

Dim fso, shell, root, logPath, cmd

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
logPath = fso.BuildPath(root, "gateway.log")

shell.CurrentDirectory = root
cmd = "cmd /c call """ & fso.BuildPath(root, "scripts\ensure_pynacl.bat") & """ && python -B -u app_v2.py >> """ & logPath & """ 2>&1"
shell.Run cmd, 0, False

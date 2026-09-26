' YT Global DL - 1-Click Dashboard Launcher
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
projectRoot = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
WshShell.CurrentDirectory = projectRoot
WshShell.Run "pythonw.exe main.py --gui", 0, False

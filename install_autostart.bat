@echo off
title Install YT Global DL to Windows Startup
echo Setting up YT Global DL to launch automatically on Windows startup...

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $sFolder = [System.Environment]::GetFolderPath('Startup'); $sFile = Join-Path $sFolder 'YT-Global-DL.lnk'; $target = (Resolve-Path '.\start_silent.vbs').Path; $sc = $ws.CreateShortcut($sFile); $sc.TargetPath = 'wscript.exe'; $sc.Arguments = '`\"' + $target + '`\"'; $sc.WorkingDirectory = (Resolve-Path '.').Path; $sc.Save(); Write-Host '[SUCCESS] Added to Windows Startup folder.' -ForegroundColor Green"

echo.
echo The daemon will now automatically run silently in the background when Windows boots.
ping 127.0.0.1 -n 3 >nul

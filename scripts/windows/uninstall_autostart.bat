@echo off
title Uninstall YT Global DL from Windows Startup
echo Removing YT Global DL from Windows startup...

powershell -NoProfile -Command "$sFolder = [System.Environment]::GetFolderPath('Startup'); $sFile = Join-Path $sFolder 'YT-Global-DL.lnk'; if (Test-Path $sFile) { Remove-Item $sFile -Force; Write-Host '[SUCCESS] Removed from Startup folder.' -ForegroundColor Green } else { Write-Host '[INFO] Shortcut was not present in Startup folder.' -ForegroundColor Yellow }"

ping 127.0.0.1 -n 3 >nul

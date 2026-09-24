@echo off
title Stop YT Global DL Daemon
echo Stopping YT Global DL background daemon on port 8765...
powershell -NoProfile -Command "$conn = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue; if ($conn) { foreach ($c in $conn) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue }; Write-Host '[SUCCESS] Daemon stopped.' -ForegroundColor Green } else { Write-Host '[INFO] Daemon is not currently running.' -ForegroundColor Yellow }"
ping 127.0.0.1 -n 2 >nul


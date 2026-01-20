@echo off
cd /d "%~dp0"
echo Starting VibeStock Monitor Service...
C:\veighna_studio\python.exe run_monitor_service.py
pause

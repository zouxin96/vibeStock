@echo off
cd /d "%~dp0"
echo Starting VibeStock Tray Monitor...
start "" "C:\veighna_studio\pythonw.exe" tray_monitor.py

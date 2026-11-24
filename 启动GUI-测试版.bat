@echo off
REM Pure-ASCII launcher: delegates to launch_gui.py which handles CJK paths.
REM It forces PYTHONPATH=src so the optimized workspace code is loaded.
"C:\Python314\python.exe" "%~dp0launch_gui.py"
if errorlevel 1 pause

@echo off
pyinstaller -F --onefile -n Outernet main.py
rmdir /s /q build
rmdir /s /q release
del /q Outernet.spec
ren dist release
xcopy /y tap\*.* release\tap\*.*
xcopy /y res\*.* release\res\*.*
pause
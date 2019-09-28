@echo off
pyinstaller -F --icon=res\icon.ico -p res --onefile -n Outernet main_window.pyw
rmdir /s /q build
rmdir /s /q release
del /q Outernet.spec
ren dist release
xcopy /y tap\*.* release\tap\*.*
xcopy /y res\*.* release\res\*.*
pause
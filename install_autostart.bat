@echo off
cd /d "%~dp0"
set PYCMD=
where py >nul 2>nul && set PYCMD=py -3
if not defined PYCMD where python >nul 2>nul && set PYCMD=python
if not defined PYCMD goto nopy
%PYCMD% autostart.py install
echo.
pause
exit /b
:nopy
echo Python bulunamadi. python.org adresinden kur, kurulumda "Add Python to PATH" kutusunu isaretle.
pause

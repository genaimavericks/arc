@echo off
echo Stopping RSW processes...

REM Stop Python API server
echo Stopping Python API server...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *api.run*" 2>nul
IF %ERRORLEVEL% EQU 0 (
    echo API server stopped successfully.
) ELSE (
    echo No API server running.
)

REM Stop Next.js development server
echo Stopping Next.js development server...
taskkill /F /IM node.exe /FI "WINDOWTITLE eq *next*" 2>nul
IF %ERRORLEVEL% EQU 0 (
    echo Next.js server stopped successfully.
) ELSE (
    echo No Next.js server running.
)

echo All RSW processes stopped.
pause

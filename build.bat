@echo off
echo Cleaning old build artifacts...
if exist main.exe del /f /q main.exe
pyinstaller main.spec --clean --noconfirm

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Moving executable to root directory...
    move /y dist\main.exe .\main.exe >nul
    
    echo Cleaning up temporary folders...
    rd /s /q build
    rd /s /q dist
    
    echo.
    echo ========================================
    echo Build Successful!
    echo Output: .\main.exe
    echo ========================================
) else (
    echo.
    echo ########################################
    echo Build Failed with error code %ERRORLEVEL%
    echo ########################################
)

pause
@echo off

REM Diagram tooling setup — uses .cmd only (no PowerShell execution policy required).



setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"



set "NPM=%ProgramFiles%\nodejs\npm.cmd"

set "NPX=%ProgramFiles%\nodejs\npx.cmd"

set "PUPPETEER_CACHE_DIR=%~dp0.puppeteer-cache"

set "CHROME_CACHE=%PUPPETEER_CACHE_DIR%\chrome-headless-shell"

set "CHROME_EXE="



if not exist "%NPM%" (

    echo ERROR: npm.cmd not found. Install Node.js from https://nodejs.org

    echo Or run once: D:\Agents\install_windows_dev.cmd

    exit /b 1

)



echo Installing Mermaid CLI...

call "%NPM%" install

if errorlevel 1 exit /b 1



REM Remove corrupted Puppeteer cache (folder exists but chrome-headless-shell.exe missing)

if exist "%CHROME_CACHE%" (

    echo Checking Puppeteer cache...

    set "CHROME_EXE_FOUND=0"

    for /r "%CHROME_CACHE%" %%F in (chrome-headless-shell.exe) do set "CHROME_EXE_FOUND=1"

    if "!CHROME_EXE_FOUND!"=="0" (

        echo Removing incomplete Puppeteer cache at:

        echo   %CHROME_CACHE%

        rmdir /s /q "%CHROME_CACHE%" 2>nul

    )

)



echo Installing Puppeteer Chrome headless shell...

call "%NPX%" puppeteer install chrome-headless-shell

if errorlevel 1 (

    echo.

    echo Retrying after full cache reset...

    rmdir /s /q "%PUPPETEER_CACHE_DIR%" 2>nul

    call "%NPX%" puppeteer install chrome-headless-shell

    if errorlevel 1 (

        echo.

        echo ERROR: Puppeteer Chrome install failed.

        echo If this persists, check your internet connection and retry.

        exit /b 1

    )

)



echo.

echo Done. Diagram rendering is ready.

echo Test: .\.venv\Scripts\python -c "from deep_research.tools.diagrams import create_diagram; ..."

echo.



endlocal

exit /b 0


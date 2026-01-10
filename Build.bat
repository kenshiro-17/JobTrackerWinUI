@echo off
setlocal enabledelayedexpansion

echo ============================================
echo    Job Tracker - Build and Package Script
echo ============================================
echo.

set "PROJECT_DIR=%~dp0"
set "PUBLISH_DIR=%PROJECT_DIR%publish"
set "DIST_DIR=%PROJECT_DIR%Distribution\JobTracker_x64"
set "INSTALLER_DIR=%PROJECT_DIR%Installer"

:: Check for required tools
where dotnet >nul 2>&1
if errorlevel 1 (
    echo ERROR: .NET SDK not found. Please install .NET 8 SDK.
    echo Download from: https://dotnet.microsoft.com/download/dotnet/8.0
    :: pause
    exit /b 1
)

:: Create directories
if exist "%PUBLISH_DIR%" rmdir /s /q "%PUBLISH_DIR%"
mkdir "%PUBLISH_DIR%"
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"
if not exist "%INSTALLER_DIR%" mkdir "%INSTALLER_DIR%"

:: Step 1: Build the project
echo [1/5] Building project...
cd /d "%PROJECT_DIR%"
dotnet build -c Release
if errorlevel 1 (
    echo ERROR: Build failed!
    :: pause
    exit /b 1
)
echo Build successful!
echo.

:: Step 2: Publish as self-contained for x64
echo [2/5] Publishing self-contained x64 build...
dotnet publish -c Release -r win-x64 --self-contained true -o "%PUBLISH_DIR%\win-x64" /p:PublishSingleFile=false /p:IncludeNativeLibrariesForSelfExtract=true
if errorlevel 1 (
    echo ERROR: Publish failed!
    :: pause
    exit /b 1
)
echo Publish successful!
echo.

:: Step 3: Prepare Distribution Folder
echo [3/5] Preparing Distribution folder...
:: Clear existing distribution to ensure clean build
rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"

:: Copy published files
xcopy "%PUBLISH_DIR%\win-x64\*" "%DIST_DIR%\" /E /Y /Q >nul

:: Copy Python script and credentials
copy "%PROJECT_DIR%gmail_job_extractor.py" "%DIST_DIR%\" >nul
if not exist "%DIST_DIR%\gmail-mcp" mkdir "%DIST_DIR%\gmail-mcp"
copy "%PROJECT_DIR%gmail-mcp\gcp-oauth.keys.json" "%DIST_DIR%\gmail-mcp\" >nul

:: Copy Assets folder (Critical for WinUI 3)
if exist "%PROJECT_DIR%Assets" (
    echo Copying Assets...
    xcopy "%PROJECT_DIR%Assets\*" "%DIST_DIR%\Assets\" /E /Y /Q >nul
) else (
    echo Warning: Assets folder not found!
)

:: Copy ICO file to root just in case
if exist "%PROJECT_DIR%Assets\JobTracker.ico" (
    copy "%PROJECT_DIR%Assets\JobTracker.ico" "%DIST_DIR%\" >nul
)

echo Distribution files prepared.
echo.

:: Step 4: Check for Inno Setup
echo [4/5] Creating installer...

set "ISCC="
set "ISCC_1=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set "ISCC_2=C:\Program Files\Inno Setup 6\ISCC.exe"

if exist "%ISCC_1%" (
    set "ISCC=%ISCC_1%"
) else if exist "%ISCC_2%" (
    set "ISCC=%ISCC_2%"
)

if defined ISCC (
    echo Inno Setup found at: "%ISCC%"
    "%ISCC%" "%PROJECT_DIR%JobTrackerInstaller.iss"
    if errorlevel 1 (
        echo ERROR: Installer creation failed!
    ) else (
        echo Installer created successfully!
        :: The installer creates OutputBaseFilename=JobTrackerInstaller in directory where .iss is run
        if exist "%PROJECT_DIR%Output\JobTrackerInstaller.exe" (
             echo Moving installer to Installer directory...
             move /Y "%PROJECT_DIR%Output\JobTrackerInstaller.exe" "%INSTALLER_DIR%\JobTrackerInstaller.exe" >nul
             echo Location: %INSTALLER_DIR%\JobTrackerInstaller.exe
        ) else if exist "%PROJECT_DIR%JobTrackerInstaller.exe" (
             move /Y "%PROJECT_DIR%JobTrackerInstaller.exe" "%INSTALLER_DIR%\JobTrackerInstaller.exe" >nul
             echo Location: %INSTALLER_DIR%\JobTrackerInstaller.exe
        ) else (
             echo Warning: Could not locate generated installer to move it. Please check project root or Output folder.
        )
    )
) else (
    echo.
    echo Inno Setup not found. Creating ZIP archive as fallback...
    echo.
    powershell -NoProfile -Command "Compress-Archive -Path '%DIST_DIR%\*' -DestinationPath '%INSTALLER_DIR%\JobTracker-1.0.0-win-x64.zip' -Force"
    echo ZIP archive created at %INSTALLER_DIR%\JobTracker-1.0.0-win-x64.zip
)

echo.
echo ============================================
echo    Build Complete!
echo ============================================
echo.
:: pause

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\Gwisp\Main",
    [ValidateSet("en", "pt", "de")]
    [string]$Language = "en",
    [switch]$CreateShortcuts,
    [switch]$NoShortcuts
)

$ErrorActionPreference = "Stop"

function Find-Python {
    $pythonCommands = @("py -3", "python")
    foreach ($command in $pythonCommands) {
        $parts = $command.Split(" ")
        $exe = $parts[0]
        $args = @($parts | Select-Object -Skip 1) + @("--version")
        try {
            & $exe @args | Out-Null
            return $command
        } catch {
            continue
        }
    }
    throw "Python 3.11+ was not found. Install Python from https://www.python.org/downloads/windows/ and run this installer again."
}

function Run-Python {
    param([string]$PythonCommand, [string[]]$Arguments)
    $parts = $PythonCommand.Split(" ")
    $exe = $parts[0]
    $baseArgs = @($parts | Select-Object -Skip 1)
    & $exe @baseArgs @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$PythonCommand failed with exit code $LASTEXITCODE"
    }
}

function Run-Executable {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Executable failed with exit code $LASTEXITCODE"
    }
}

function New-AppShortcut {
    param(
        [string]$ShortcutPath,
        [string]$TargetPath,
        [string]$WorkingDirectory,
        [string]$Description,
        [string]$IconPath
    )

    try {
        $shortcutFolder = Split-Path -Parent $ShortcutPath
        New-Item -ItemType Directory -Force -Path $shortcutFolder | Out-Null

        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($ShortcutPath)
        $shortcut.TargetPath = $TargetPath
        $shortcut.WorkingDirectory = $WorkingDirectory
        $shortcut.Description = $Description
        if (Test-Path -LiteralPath $IconPath) {
            $shortcut.IconLocation = $IconPath
        }
        $shortcut.Save()
    } catch {
        Write-Host "Shortcut was not created: ${ShortcutPath}. $($_.Exception.Message)"
    }
}

function Set-GwispConfigLanguage {
    param(
        [string]$ConfigPath,
        [string]$Language
    )

    try {
        $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
        $config | Add-Member -NotePropertyName "language" -NotePropertyValue $Language -Force
        $config | ConvertTo-Json -Depth 8 | Set-Content -Path $ConfigPath -Encoding UTF8
    } catch {
        throw "Could not set Gwisp language in config.json: $($_.Exception.Message)"
    }
}

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PayloadDir = Join-Path $PackageRoot "payload"

if (-not (Test-Path -LiteralPath $PayloadDir)) {
    throw "Installer payload folder not found: $PayloadDir"
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Get-ChildItem -LiteralPath $PayloadDir -Force | Copy-Item -Destination $InstallDir -Recurse -Force

$PythonCommand = Find-Python
$VenvDir = Join-Path $InstallDir ".venv"
Run-Python $PythonCommand @("-m", "venv", $VenvDir)

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
Run-Executable $VenvPython @("-m", "pip", "install", "--upgrade", "pip")
Run-Executable $VenvPython @("-m", "pip", "install", "-r", (Join-Path $InstallDir "requirements.txt"))

$ConfigPath = Join-Path $InstallDir "config.json"
if (-not (Test-Path -LiteralPath $ConfigPath)) {
    Copy-Item -LiteralPath (Join-Path $InstallDir "config.example.json") -Destination $ConfigPath
}
Set-GwispConfigLanguage -ConfigPath $ConfigPath -Language $Language

$LauncherPath = Join-Path $InstallDir "Run-Gwisp-Main.bat"
@"
@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" run_gwisp.py
pause
"@ | Set-Content -Path $LauncherPath -Encoding ASCII

if ($CreateShortcuts -and -not $NoShortcuts) {
    $IconPath = Join-Path $InstallDir "src\gwisp\assets\gwisp_xp.ico"
    $ProgramsDir = [Environment]::GetFolderPath("Programs")
    $DesktopDir = [Environment]::GetFolderPath("Desktop")
    $ShortcutName = "Gwisp Main.lnk"

    New-AppShortcut `
        -ShortcutPath (Join-Path (Join-Path $ProgramsDir "Gwisp") $ShortcutName) `
        -TargetPath $LauncherPath `
        -WorkingDirectory $InstallDir `
        -Description "Gwisp Main" `
        -IconPath $IconPath

    New-AppShortcut `
        -ShortcutPath (Join-Path $DesktopDir $ShortcutName) `
        -TargetPath $LauncherPath `
        -WorkingDirectory $InstallDir `
        -Description "Gwisp Main" `
        -IconPath $IconPath
}

Write-Host ""
Write-Host "Gwisp Main installed successfully."
Write-Host "Install folder: $InstallDir"
Write-Host "Launcher: $LauncherPath"
Write-Host ""
Write-Host "Before first use, install/configure Tesseract OCR and Ollama on this machine."


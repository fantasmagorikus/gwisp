param(
    [string]$InstallDir = "$env:LOCALAPPDATA\Gwisp\Main",
    [ValidateSet("en", "pt", "de")]
    [string]$Language = "en",
    [ValidateSet("ollama", "cloud")]
    [string]$LlmProvider = "ollama",
    [string]$CloudApiUrl = "",
    [string]$CloudModel = "",
    [string]$CloudApiKey = "",
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

function Set-GwispConfig {
    param(
        [string]$ConfigPath,
        [string]$Language,
        [string]$LlmProvider,
        [string]$CloudApiUrl,
        [string]$CloudModel,
        [string]$CloudApiKey
    )

    try {
        $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
        $config | Add-Member -NotePropertyName "language" -NotePropertyValue $Language -Force
        $config | Add-Member -NotePropertyName "llm_provider" -NotePropertyValue $LlmProvider -Force

        if ($LlmProvider -eq "cloud") {
            if ($CloudApiUrl.Trim().Length -gt 0) {
                $config | Add-Member -NotePropertyName "cloud_api_url" -NotePropertyValue $CloudApiUrl.Trim() -Force
            }
            if ($CloudModel.Trim().Length -gt 0) {
                $config | Add-Member -NotePropertyName "cloud_model" -NotePropertyValue $CloudModel.Trim() -Force
            }
            if ($CloudApiKey.Trim().Length -gt 0) {
                $config | Add-Member -NotePropertyName "cloud_api_key" -NotePropertyValue $CloudApiKey.Trim() -Force
            }
        }

        $config | ConvertTo-Json -Depth 8 | Set-Content -Path $ConfigPath -Encoding UTF8
    } catch {
        throw "Could not set Gwisp config.json values: $($_.Exception.Message)"
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
$EffectiveCloudApiKey = $CloudApiKey
if ($EffectiveCloudApiKey.Trim().Length -eq 0 -and $env:GWISP_SETUP_CLOUD_API_KEY) {
    $EffectiveCloudApiKey = $env:GWISP_SETUP_CLOUD_API_KEY
}

Set-GwispConfig `
    -ConfigPath $ConfigPath `
    -Language $Language `
    -LlmProvider $LlmProvider `
    -CloudApiUrl $CloudApiUrl `
    -CloudModel $CloudModel `
    -CloudApiKey $EffectiveCloudApiKey

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
if ($LlmProvider -eq "cloud") {
    Write-Host "AI provider: Cloud API."
    if ($EffectiveCloudApiKey.Trim().Length -gt 0) {
        Write-Host "Cloud API key saved only in the local config.json file."
    } else {
        Write-Host "Set GWISP_CLOUD_API_KEY before running Gwisp if your provider requires a key."
    }
} else {
    Write-Host "AI provider: Local Ollama. Install Ollama and pull the configured model before first use."
}
Write-Host "Before first use, install/configure Tesseract OCR."


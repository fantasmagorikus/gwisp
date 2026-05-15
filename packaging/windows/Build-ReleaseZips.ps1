$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$BuildRoot = Join-Path $RepoRoot "build\release-zips"
$DownloadsDir = Join-Path $RepoRoot "downloads"

$RuntimeItems = @(
    "src",
    "run_gwisp.py",
    "run_gwisp_sync_ocr.py",
    "requirements.txt",
    "pyproject.toml",
    "config.example.json",
    "README.md",
    "SUPPORT.md",
    "LICENSE",
    "SECURITY.md",
    "docs"
)

$ExcludedDirectoryNames = @(
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".git",
    ".tools",
    ".venv",
    "venv",
    "build",
    "dist"
)

$ExcludedFilePatterns = @(
    "*.pyc",
    "*.pyo",
    "*.log",
    "config.json"
)

function Test-ExcludedRelativePath {
    param([string]$RelativePath)

    $segments = $RelativePath -split "[\\/]+"
    foreach ($segment in $segments) {
        if ($ExcludedDirectoryNames -contains $segment -or $segment -like "*.egg-info") {
            return $true
        }
    }

    $leafName = Split-Path -Leaf $RelativePath
    foreach ($pattern in $ExcludedFilePatterns) {
        if ($leafName -like $pattern) {
            return $true
        }
    }

    return $false
}

function Copy-PayloadItem {
    param(
        [string]$Source,
        [string]$Destination
    )

    $sourceItem = Get-Item -LiteralPath $Source -Force
    if (-not $sourceItem.PSIsContainer) {
        if (Test-ExcludedRelativePath -RelativePath $sourceItem.Name) {
            return
        }

        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
        Copy-Item -LiteralPath $sourceItem.FullName -Destination $Destination -Force
        return
    }

    $sourceRoot = $sourceItem.FullName.TrimEnd("\")
    Get-ChildItem -LiteralPath $sourceItem.FullName -Recurse -Force -File | ForEach-Object {
        $relativePath = $_.FullName.Substring($sourceRoot.Length).TrimStart("\")
        if (-not (Test-ExcludedRelativePath -RelativePath $relativePath)) {
            $destinationPath = Join-Path $Destination $relativePath
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destinationPath) | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $destinationPath -Force
        }
    }
}

function Copy-RuntimePayload {
    param([string]$Destination)

    $PayloadDir = Join-Path $Destination "payload"
    New-Item -ItemType Directory -Force -Path $PayloadDir | Out-Null

    foreach ($item in $RuntimeItems) {
        $source = Join-Path $RepoRoot $item
        if (-not (Test-Path -LiteralPath $source)) {
            throw "Runtime payload item not found: $source"
        }
        Copy-PayloadItem -Source $source -Destination (Join-Path $PayloadDir $item)
    }
}

function Invoke-WithRetry {
    param(
        [scriptblock]$ScriptBlock,
        [string]$Description,
        [int]$Attempts = 5,
        [int]$DelayMilliseconds = 700
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            & $ScriptBlock
            return
        } catch {
            if ($attempt -eq $Attempts) {
                throw
            }

            Write-Host "$Description failed on attempt $attempt. Retrying..."
            Start-Sleep -Milliseconds $DelayMilliseconds
        }
    }
}

function New-InstallerZip {
    param(
        [string]$Name,
        [string]$InstallerScript,
        [string]$ReadmeFile
    )

    $StageDir = Join-Path $BuildRoot $Name
    if (Test-Path -LiteralPath $StageDir) {
        Remove-Item -LiteralPath $StageDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $StageDir | Out-Null

    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $InstallerScript) -Destination $StageDir
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $ReadmeFile) -Destination (Join-Path $StageDir "README_FIRST.txt")
    Copy-RuntimePayload -Destination $StageDir

    $ZipPath = Join-Path $DownloadsDir "$Name.zip"
    $TempZipPath = Join-Path ([System.IO.Path]::GetTempPath()) "$Name-$([Guid]::NewGuid().ToString("N")).zip"

    try {
        Invoke-WithRetry `
            -Description "Compressing $Name" `
            -ScriptBlock {
                if (Test-Path -LiteralPath $TempZipPath) {
                    Remove-Item -LiteralPath $TempZipPath -Force
                }
                Compress-Archive -Path (Join-Path $StageDir "*") -DestinationPath $TempZipPath -CompressionLevel Optimal
            }

        Invoke-WithRetry `
            -Description "Replacing $ZipPath" `
            -ScriptBlock {
                if (Test-Path -LiteralPath $ZipPath) {
                    Remove-Item -LiteralPath $ZipPath -Force
                }
                Move-Item -LiteralPath $TempZipPath -Destination $ZipPath -Force
            }
    } finally {
        if (Test-Path -LiteralPath $TempZipPath) {
            Remove-Item -LiteralPath $TempZipPath -Force -ErrorAction SilentlyContinue
        }
    }

    Write-Host $ZipPath
}

New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null
New-Item -ItemType Directory -Force -Path $DownloadsDir | Out-Null

New-InstallerZip `
    -Name "Gwisp-Main-Windows" `
    -InstallerScript "Install-Gwisp-Main.ps1" `
    -ReadmeFile "README-Gwisp-Main.txt"

New-InstallerZip `
    -Name "Gwisp-SyncOCR-Windows" `
    -InstallerScript "Install-Gwisp-SyncOCR.ps1" `
    -ReadmeFile "README-Gwisp-SyncOCR.txt"

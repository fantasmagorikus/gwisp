param(
    [switch]$SkipZipBuild,
    [switch]$Sign,
    [string]$CertificateThumbprint = "",
    [string]$CertificatePath = "",
    [string]$CertificatePassword = "",
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [switch]$RequireSigned
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$DownloadsDir = Join-Path $RepoRoot "downloads"
$BuildRoot = Join-Path $RepoRoot "build\bootstrapper"
$SourcePath = Join-Path $PSScriptRoot "bootstrapper\GwispSetup.cs"
$OutputPath = Join-Path $DownloadsDir "Gwisp-Setup.exe"
$ReadmeOutputPath = Join-Path $DownloadsDir "Gwisp-Setup.README.txt"
$ChecksumOutputPath = Join-Path $DownloadsDir "SHA256SUMS.txt"
$IconPath = Join-Path $RepoRoot "src\gwisp\assets\gwisp_xp.ico"
$MainZipPath = Join-Path $DownloadsDir "Gwisp-Main-Windows.zip"
$SyncZipPath = Join-Path $DownloadsDir "Gwisp-SyncOCR-Windows.zip"
$GeneratedHashSourcePath = Join-Path $BuildRoot "GwispSetup.PackageHashes.g.cs"

function Find-CSharpCompiler {
    $command = Get-Command csc.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $frameworkCompiler = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    if (Test-Path -LiteralPath $frameworkCompiler) {
        return $frameworkCompiler
    }

    throw "csc.exe was not found. Install .NET Framework developer tools or the .NET SDK, then run this build script again."
}

function Find-SignTool {
    $command = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $kitsRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    if (Test-Path -LiteralPath $kitsRoot) {
        $candidate = Get-ChildItem -LiteralPath $kitsRoot -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "\\x64\\signtool\.exe$" } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($candidate) {
            return $candidate.FullName
        }
    }

    throw "signtool.exe was not found. Install the Windows SDK or add signtool.exe to PATH."
}

function New-PackageHashSource {
    param(
        [string]$MainZip,
        [string]$SyncZip,
        [string]$Output
    )

    if (-not (Test-Path -LiteralPath $MainZip)) {
        throw "Main ZIP not found for hash embedding: $MainZip"
    }
    if (-not (Test-Path -LiteralPath $SyncZip)) {
        throw "Sync OCR ZIP not found for hash embedding: $SyncZip"
    }

    $mainHash = (Get-FileHash -LiteralPath $MainZip -Algorithm SHA256).Hash.ToLowerInvariant()
    $syncHash = (Get-FileHash -LiteralPath $SyncZip -Algorithm SHA256).Hash.ToLowerInvariant()

    @"
namespace GwispSetup
{
    internal sealed partial class InstallerForm
    {
        private const string MainZipSha256 = "$mainHash";
        private const string SyncZipSha256 = "$syncHash";
    }
}
"@ | Set-Content -Path $Output -Encoding ASCII
}

function Invoke-AuthenticodeSign {
    param([string]$Path)

    if (-not $Sign) {
        return
    }

    $signTool = Find-SignTool
    $arguments = @(
        "sign",
        "/fd", "SHA256",
        "/td", "SHA256",
        "/tr", $TimestampUrl
    )

    if ($CertificateThumbprint.Trim().Length -gt 0) {
        $arguments += @("/sha1", $CertificateThumbprint.Trim())
    } elseif ($CertificatePath.Trim().Length -gt 0) {
        $arguments += @("/f", $CertificatePath.Trim())
        if ($CertificatePassword.Length -gt 0) {
            $arguments += @("/p", $CertificatePassword)
        }
    } else {
        throw "Use -CertificateThumbprint or -CertificatePath when -Sign is set."
    }

    $arguments += $Path
    & $signTool @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "signtool sign failed with exit code $LASTEXITCODE"
    }

    & $signTool verify /pa /v $Path
    if ($LASTEXITCODE -ne 0) {
        throw "signtool verify failed with exit code $LASTEXITCODE"
    }
}

function Assert-SignedIfRequired {
    param([string]$Path)

    $signature = Get-AuthenticodeSignature -LiteralPath $Path
    if ($RequireSigned -and $signature.Status -ne "Valid") {
        throw "Installer is not Authenticode-signed with a trusted certificate. Status: $($signature.Status). $($signature.StatusMessage)"
    }

    Write-Host "Authenticode status: $($signature.Status)"
}

function Write-Checksums {
    param([string[]]$Paths)

    $lines = foreach ($path in $Paths) {
        if (Test-Path -LiteralPath $path) {
            $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
            "{0}  {1}" -f $hash, (Split-Path -Leaf $path)
        }
    }

    $lines | Set-Content -Path $ChecksumOutputPath -Encoding ASCII
    Write-Host $ChecksumOutputPath
}

if (-not $SkipZipBuild) {
    & (Join-Path $PSScriptRoot "Build-ReleaseZips.ps1")
    if (-not $?) {
        throw "Build-ReleaseZips.ps1 failed"
    }
}

New-Item -ItemType Directory -Force -Path $DownloadsDir | Out-Null
New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null

New-PackageHashSource -MainZip $MainZipPath -SyncZip $SyncZipPath -Output $GeneratedHashSourcePath

$compiler = Find-CSharpCompiler
$references = @(
    "/reference:System.Windows.Forms.dll",
    "/reference:System.Drawing.dll",
    "/reference:System.IO.Compression.dll",
    "/reference:System.IO.Compression.FileSystem.dll"
)

$arguments = @(
    "/nologo",
    "/target:winexe",
    "/optimize+",
    "/out:$OutputPath"
) + $references

if (Test-Path -LiteralPath $IconPath) {
    $arguments += "/win32icon:$IconPath"
}

$arguments += $SourcePath
$arguments += $GeneratedHashSourcePath

& $compiler @arguments
if ($LASTEXITCODE -ne 0) {
    throw "C# compiler failed with exit code $LASTEXITCODE"
}

$selfTest = Start-Process -FilePath $OutputPath -ArgumentList "--self-test" -Wait -PassThru
if ($selfTest.ExitCode -ne 0) {
    throw "Bootstrapper self-test failed with exit code $($selfTest.ExitCode)"
}

Invoke-AuthenticodeSign -Path $OutputPath
Assert-SignedIfRequired -Path $OutputPath

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README-Gwisp-Setup.txt") -Destination $ReadmeOutputPath -Force
Write-Checksums -Paths @($OutputPath, $MainZipPath, $SyncZipPath, $ReadmeOutputPath)

Write-Host $OutputPath

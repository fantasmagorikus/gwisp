param(
    [switch]$SkipZipBuild
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$DownloadsDir = Join-Path $RepoRoot "downloads"
$BuildRoot = Join-Path $RepoRoot "build\bootstrapper"
$SourcePath = Join-Path $PSScriptRoot "bootstrapper\GwispSetup.cs"
$OutputPath = Join-Path $DownloadsDir "Gwisp-Setup.exe"
$ReadmeOutputPath = Join-Path $DownloadsDir "Gwisp-Setup.README.txt"
$IconPath = Join-Path $RepoRoot "src\gwisp\assets\gwisp_xp.ico"

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

if (-not $SkipZipBuild) {
    & (Join-Path $PSScriptRoot "Build-ReleaseZips.ps1")
    if (-not $?) {
        throw "Build-ReleaseZips.ps1 failed"
    }
}

New-Item -ItemType Directory -Force -Path $DownloadsDir | Out-Null
New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null

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

& $compiler @arguments
if ($LASTEXITCODE -ne 0) {
    throw "C# compiler failed with exit code $LASTEXITCODE"
}

$selfTest = Start-Process -FilePath $OutputPath -ArgumentList "--self-test" -Wait -PassThru
if ($selfTest.ExitCode -ne 0) {
    throw "Bootstrapper self-test failed with exit code $($selfTest.ExitCode)"
}

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README-Gwisp-Setup.txt") -Destination $ReadmeOutputPath -Force

Write-Host $OutputPath


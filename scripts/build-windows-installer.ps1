param(
    [string]$IsccPath = '',
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
if (-not $IsccPath) {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) {
        $IsccPath = $command.Source
    } else {
        $IsccPath = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
    }
}
if (-not (Test-Path -LiteralPath $IsccPath -PathType Leaf)) {
    throw 'Install Inno Setup 6 or pass -IsccPath with the compiler location.'
}

Push-Location $projectRoot
try {
    $metadata = cargo metadata --manifest-path desktop-rust/Cargo.toml --no-deps --format-version 1 --locked
    if ($LASTEXITCODE -ne 0) { throw 'Could not read Rust package metadata.' }
    $metadata = ($metadata -join "`n") | ConvertFrom-Json
    $package = $metadata.packages | Where-Object name -eq 'artfinder-desktop'
    $version = $package.version
    if ($version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid Rust package version.' }
    if ($env:GITHUB_REF_TYPE -eq 'tag' -and $env:GITHUB_REF_NAME -ne "v$version") {
        throw "Release tag must match ArtFinder version v$version."
    }

    if (-not $SkipBuild) {
        cargo build --manifest-path desktop-rust/Cargo.toml --release --locked
        if ($LASTEXITCODE -ne 0) { throw 'Rust build failed.' }
    }
    $binary = Join-Path $metadata.target_directory 'release/artfinder-desktop.exe'
    New-Item -ItemType Directory -Force 'dist/review' | Out-Null
    Copy-Item -LiteralPath $binary -Destination 'dist/review/ArtFinder.exe'
    $executable = (Resolve-Path -LiteralPath 'dist/review/ArtFinder.exe').Path
    & $IsccPath "/DAppVersion=$version" "/DAppExecutable=$executable" 'packaging/windows/artfinder.iss' | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
    Get-Item -LiteralPath "dist/review/ArtFinder-Setup-$version.exe"
} finally {
    Pop-Location
}

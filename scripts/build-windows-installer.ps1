param(
    [string]$AppVersion = '0.0.0-dev',
    [string]$IsccPath = '',
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
if ($AppVersion -notmatch '^\d+\.\d+\.\d+(?:[-.][A-Za-z0-9.-]+)?$') {
    throw 'Use a version such as 1.0.0 or 1.0.0-dev.'
}
$projectRoot = Split-Path $PSScriptRoot -Parent
if (-not $IsccPath) {
    $compilerCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($compilerCommand) { $IsccPath = $compilerCommand.Source }
    else { $IsccPath = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe' }
}
if (-not (Test-Path -LiteralPath $IsccPath -PathType Leaf)) {
    throw 'Install Inno Setup 6 or pass -IsccPath with the compiler location.'
}
Push-Location $projectRoot
try {
    if (-not $SkipBuild) {
        & venv/Scripts/python.exe -m PyInstaller --noconfirm --distpath dist/review --workpath build/windows-review artfinder.spec
        if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }
    }
    $appExecutable = (Resolve-Path -LiteralPath 'dist/review/ArtFinder.exe').Path
    & venv/Scripts/python.exe scripts/verify-windows-package.py $appExecutable
    if ($LASTEXITCODE -ne 0) { throw 'Package validation failed; installer was not generated.' }
    & $IsccPath "/DAppVersion=$AppVersion" "/DAppExecutable=$appExecutable" 'packaging/windows/artfinder.iss'
    if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
    Get-Item -LiteralPath "dist/review/ArtFinder-Setup-$AppVersion.exe"
} finally { Pop-Location }

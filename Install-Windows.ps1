$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'dist\DPS Design Studio'
$target = Join-Path $env:LOCALAPPDATA 'DPSDesignStudio'
if (!(Test-Path (Join-Path $source 'DPS Design Studio.exe'))) { throw 'Build the Windows application first.' }
New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Path (Join-Path $source '*') -Destination $target -Recurse -Force
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcut = $shell.CreateShortcut((Join-Path $desktop 'DPS Design Studio.lnk'))
$shortcut.TargetPath = Join-Path $target 'DPS Design Studio.exe'
$shortcut.WorkingDirectory = $target
$shortcut.Save()
Write-Host "Installed to $target"

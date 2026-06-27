# uninstall-gobblescript.ps1
# Removes everything install-gobblescript.ps1 added: the .gob association
# and the GobbleScript.File registry entries (including artifacts from
# older versions of the installer). Does NOT touch gobblescript.py,
# gobblescript_canvas.py, gobblescript_textgui.py, or your .gob files.

$ErrorActionPreference = "SilentlyContinue"
$root = $PSScriptRoot
$classesRoot = "HKCU:\Software\Classes"

Write-Host ""
Write-Host "Removing GobbleScript file association..." -ForegroundColor Cyan

Remove-Item -Path "$classesRoot\.gob" -Recurse -Force
Remove-Item -Path "$classesRoot\GobbleScript.File" -Recurse -Force

# leftover from an older version of the installer, if present
$legacyWrapper = Join-Path $root "Run-GobbleScript-Text.bat"
if (Test-Path $legacyWrapper) {
    Remove-Item -Path $legacyWrapper -Force
    Write-Host "Removed $legacyWrapper"
}

Add-Type -Namespace GobbleShell -Name Notify -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("shell32.dll")]
public static extern void SHChangeNotify(long wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
'@
[GobbleShell.Notify]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)

Write-Host "Done. .gob files are no longer associated with GobbleScript." -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to close"

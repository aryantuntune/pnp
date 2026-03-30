@echo off
setlocal

echo ============================================
echo   SSMSPL - Direct Printing Setup
echo ============================================
echo.
echo Creates browser shortcuts on your Desktop
echo that print receipts without any popup.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $shell = New-Object -ComObject WScript.Shell; $flag = '--kiosk-printing'; $desk = [System.Environment]::GetFolderPath('Desktop'); $created = 0; $browsers = @( @{ Name='Google Chrome'; Short='Chrome - Direct Print'; Paths=@('C:\Program Files\Google\Chrome\Application\chrome.exe','C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',($env:LOCALAPPDATA + '\Google\Chrome\Application\chrome.exe')) }, @{ Name='Microsoft Edge'; Short='Edge - Direct Print'; Paths=@('C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe','C:\Program Files\Microsoft\Edge\Application\msedge.exe',($env:LOCALAPPDATA + '\Microsoft\Edge\Application\msedge.exe')) } ); foreach ($b in $browsers) { $exe = $null; foreach ($p in $b.Paths) { if (Test-Path $p) { $exe = $p; break } }; if ($exe) { $lnkPath = $desk + '\' + $b.Short + '.lnk'; $lnk = $shell.CreateShortcut($lnkPath); $lnk.TargetPath = $exe; $lnk.Arguments = $flag; $lnk.Save(); Write-Host ('  Created: ' + $lnkPath) -ForegroundColor Green; $created++ } else { Write-Host ('  Not installed: ' + $b.Name) -ForegroundColor DarkGray } }; Write-Host ''; if ($created -gt 0) { Write-Host ('Done! ' + $created + ' shortcut(s) added to your Desktop.') -ForegroundColor Cyan; Write-Host ''; Write-Host 'NEXT STEPS:' -ForegroundColor Yellow; Write-Host '  1. Close ALL open browser windows completely.' -ForegroundColor White; Write-Host '  2. Open the new shortcut on your Desktop:' -ForegroundColor White; Write-Host '       Chrome - Direct Print   or   Edge - Direct Print' -ForegroundColor White; Write-Host '  3. Always use this shortcut to open the browser for ticketing.' -ForegroundColor White } else { Write-Host 'Chrome and Edge were not found. Please install one and run this again.' -ForegroundColor Red } }"

echo.
pause

@echo off
setlocal

echo ============================================
echo   SSMSPL - Direct Printing Setup
echo ============================================
echo.
echo This configures Chrome and Edge to send
echo print jobs directly to the printer without
echo showing the print dialog popup.
echo.
echo Running setup...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $flag = '--kiosk-printing'; $shell = New-Object -ComObject WScript.Shell; $paths = @( [System.Environment]::GetFolderPath('Desktop') + '\Google Chrome.lnk', [System.Environment]::GetFolderPath('Desktop') + '\Microsoft Edge.lnk', $env:APPDATA + '\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\Google Chrome.lnk', $env:APPDATA + '\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\Microsoft Edge.lnk', $env:APPDATA + '\Microsoft\Windows\Start Menu\Programs\Google Chrome.lnk', $env:APPDATA + '\Microsoft\Windows\Start Menu\Programs\Microsoft Edge.lnk', 'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Google Chrome.lnk', 'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Microsoft Edge.lnk' ); $updated = 0; foreach ($p in $paths) { if (Test-Path $p) { try { $lnk = $shell.CreateShortcut($p); if ($lnk.Arguments -notlike '*kiosk-printing*') { if ($lnk.Arguments) { $lnk.Arguments = $lnk.Arguments + ' ' + $flag } else { $lnk.Arguments = $flag }; $lnk.Save(); Write-Host ('  Updated: ' + $p) -ForegroundColor Green; $updated++ } else { Write-Host ('  Already configured: ' + $p) -ForegroundColor Yellow } } catch { Write-Host ('  Skipped (no access): ' + $p) -ForegroundColor DarkGray } } }; Write-Host ''; if ($updated -gt 0) { Write-Host ('Setup complete! ' + $updated + ' shortcut(s) updated.') -ForegroundColor Cyan; Write-Host 'ACTION REQUIRED: Close all browser windows and reopen from your desktop shortcut.' -ForegroundColor White } else { Write-Host 'All shortcuts are already configured for direct printing.' -ForegroundColor Green } }"

echo.
pause

@echo off
setlocal

echo ============================================
echo   SSMSPL - Direct Printing Setup
echo ============================================
echo.
echo Importing SSMSPL certificate into QZ Tray
echo for silent receipt printing (no popups).
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "& {
  # ── SSMSPL certificate entry (exact format QZ Tray uses in allowed.dat) ──
  $fingerprint = 'd35d31216249c0520601f03d194fba20ea3df0cf'
  $entry       = \"$fingerprint`tSSMSPL POS`tSSMSPL`t2026-03-31 20:08:58`t2036-03-28 20:08:58`ttrue\"

  $qzDir      = [System.IO.Path]::Combine($env:APPDATA, 'qz')
  $allowedDat = [System.IO.Path]::Combine($qzDir, 'allowed.dat')
  $blockedDat = [System.IO.Path]::Combine($qzDir, 'blocked.dat')

  try {
    # ── Create qz directory if QZ Tray has never run yet ──
    if (-not (Test-Path $qzDir)) {
      New-Item -ItemType Directory -Force -Path $qzDir | Out-Null
      Write-Host '  Created QZ Tray data directory.' -ForegroundColor DarkGray
    }

    # ── Remove from blocked.dat if it was ever blocked ──
    if (Test-Path $blockedDat) {
      $blocked = [System.IO.File]::ReadAllText($blockedDat, [System.Text.Encoding]::UTF8)
      if ($blocked -like \"*$fingerprint*\") {
        $lines = $blocked -split \"`n\" | Where-Object { $_ -notlike \"*$fingerprint*\" }
        [System.IO.File]::WriteAllText($blockedDat, ($lines -join \"`n\"), [System.Text.Encoding]::UTF8)
        Write-Host '  Removed from blocked list.' -ForegroundColor Yellow
      }
    }

    # ── Add to allowed.dat if not already present ──
    $alreadyTrusted = $false
    if (Test-Path $allowedDat) {
      $existing = [System.IO.File]::ReadAllText($allowedDat, [System.Text.Encoding]::UTF8)
      if ($existing -like \"*$fingerprint*\") { $alreadyTrusted = $true }
    }

    if ($alreadyTrusted) {
      Write-Host '  Certificate already trusted — nothing to do.' -ForegroundColor Green
    } else {
      [System.IO.File]::AppendAllText($allowedDat, $entry + \"`n\", [System.Text.Encoding]::UTF8)
      Write-Host '  Certificate added to QZ Tray trusted list.' -ForegroundColor Green
    }

    # ── Restart QZ Tray if running so it picks up the new entry ──
    $qzProc = Get-Process -Name 'qz-tray' -ErrorAction SilentlyContinue
    if ($qzProc) {
      Write-Host '  Restarting QZ Tray...' -ForegroundColor Yellow
      Stop-Process -Name 'qz-tray' -Force -ErrorAction SilentlyContinue
      Start-Sleep -Seconds 2
      $qzExePaths = @(
        'C:\Program Files\QZ Tray\qz-tray.exe',
        'C:\Program Files (x86)\QZ Tray\qz-tray.exe',
        ([System.IO.Path]::Combine($env:LOCALAPPDATA, 'QZ Tray', 'qz-tray.exe'))
      )
      foreach ($p in $qzExePaths) {
        if (Test-Path $p) { Start-Process $p; break }
      }
      Write-Host '  QZ Tray restarted.' -ForegroundColor Green
    } else {
      Write-Host '  QZ Tray is not running. Start it from the Start Menu.' -ForegroundColor Yellow
    }

    Write-Host ''
    Write-Host '  DONE. Receipts will now print silently.' -ForegroundColor Cyan

  } catch {
    Write-Host ''
    Write-Host ('  ERROR: ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host ''
    Write-Host '  Manual fallback:' -ForegroundColor Yellow
    Write-Host '    1. Right-click QZ Tray icon in system tray' -ForegroundColor White
    Write-Host '    2. Open Site Manager -> click +' -ForegroundColor White
    Write-Host '    3. Import: D:\workspace\ssmspl\ssmspl-qz.crt' -ForegroundColor White
  }
}"

echo.
pause

# XuanShu v.0.1.0 - reproducible Windows acceptance.
# Run in the extracted project: powershell -ExecutionPolicy Bypass -File .\scripts\windows_acceptance.ps1
# This installs Python dependencies into .venv only, never into the global Python.
[CmdletBinding()]
param(
  [switch]$SkipBrowser,
  [switch]$SkipProfessional,
  [switch]$SkipDocker,
  [switch]$NoInstall
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
$python = Join-Path $root '.venv\Scripts\python.exe'
function Invoke-Checked {
  param([string]$Label, [scriptblock]$Action)
  Write-Host "==> $Label"
  & $Action
  if ($LASTEXITCODE -ne 0) { throw "$Label failed, exit $LASTEXITCODE" }
}
if (-not (Test-Path (Join-Path $root 'AGENTS.md'))) { throw 'Not a XuanShu project directory' }
if (-not (Test-Path (Join-Path $root 'pyproject.toml'))) { throw 'Missing pyproject.toml' }
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $NoInstall) {
  if (-not (Test-Path $python)) {
    if ($uv) { Invoke-Checked 'Create isolated Python venv' { uv venv --python 3.15 .venv } }
    else { Invoke-Checked 'Create isolated Python venv' { py -3.15 -m venv .venv } }
  }
  if ($uv) {
    Invoke-Checked 'Install project and test dependencies' { uv pip install --python $python -r requirements-dev.txt -e . pip setuptools wheel }
    if (-not $SkipProfessional) {
      Invoke-Checked 'Install optional professional Zi Wei' { uv pip install --python $python 'iztro-py==0.5.0' }
    }
    if (-not $SkipBrowser) { Invoke-Checked 'Install Playwright browser driver' { uv pip install --python $python playwright } }
  } else {
    Invoke-Checked 'Install packaging tools' { & $python -m pip install --upgrade pip setuptools wheel }
    Invoke-Checked 'Install project and test dependencies' { & $python -m pip install -r requirements-dev.txt -e . }
    if (-not $SkipProfessional) {
      Invoke-Checked 'Install optional professional Zi Wei' { & $python -m pip install 'iztro-py==0.5.0' }
    }
    if (-not $SkipBrowser) { Invoke-Checked 'Install Playwright browser driver' { & $python -m pip install playwright } }
  }
}
if (-not (Test-Path $python)) { throw "No project venv Python: $python" }
Invoke-Checked 'Automated unit/regression tests' { & $python -m pytest -q }
Invoke-Checked 'Isolated wheel installation smoke' { & $python scripts/wheel_smoke.py }
Invoke-Checked 'All MCP tools vs REST functional audit' { & $python scripts/full_functional_audit.py }
Invoke-Checked 'Real loopback TCP HTTP smoke' { & $python scripts/http_smoke.py }
Invoke-Checked 'CLI smoke' { & $python -m app.cli bazi --date 2000-08-16T04:00 --tz Asia/Shanghai | Out-Null }
$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) { Invoke-Checked 'AES-GCM browser backup in Node' { node tests/vault_smoke.cjs } }
else { Write-Warning 'Node.js not found; vault smoke skipped' }
if (-not $SkipBrowser) {
  $chrome = @('C:\Program Files\Google\Chrome\Application\chrome.exe',
              'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe') |
            Where-Object { Test-Path $_ } | Select-Object -First 1
  if ($chrome) { Invoke-Checked 'Real Chrome DOM with FastAPI bridge' { & $python scripts/browser_smoke.py --chromium $chrome } }
  if ($chrome) { Invoke-Checked 'Real Chrome-to-HTTP E2E (no bridge)' { & $python scripts/windows_browser_e2e.py --chromium $chrome } }
  else { Write-Warning 'Chrome not found; browser test skipped' }
}
if (-not $SkipDocker) {
  $docker = Get-Command docker -ErrorAction SilentlyContinue
  if ($docker) {
    try {
      $engineStatus = & docker info --format '{{.ServerVersion}}' 2>&1
      if ($LASTEXITCODE -eq 0) {
        Write-Host 'Docker engine available (container image run is separately opt-in: docker compose up --build).'
      } else { Write-Warning 'Docker CLI found but engine not running; container acceptance blocked' }
    } catch { Write-Warning 'Docker CLI found but engine not running; container acceptance blocked' }
  } else { Write-Warning 'Docker missing; container acceptance blocked' }
}
Write-Host 'Windows local acceptance finished. The project is still pre-release v.0.1.0.'

$ErrorActionPreference = "Continue"

$currentPid = $PID
try {
    $allProcesses = Get-CimInstance Win32_Process -ErrorAction Stop
} catch {
    Write-Host ("[WARN] Could not inspect Win32_Process for stale Streamlit cleanup: {0}" -f $_.Exception.Message)
    exit 0
}

$processes = $allProcesses | Where-Object {
    $_.ProcessId -ne $currentPid -and
    $_.CommandLine -and
    $_.CommandLine -match "streamlit" -and
    $_.CommandLine -match "dating_assistant[\\/]+gui_streamlit_app\.py"
}

if (-not $processes) {
    Write-Host "No stale dating_assistant Streamlit process found."
    exit 0
}

foreach ($process in $processes) {
    Write-Host ("Stopping stale dating_assistant Streamlit PID {0}" -f $process.ProcessId)
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

exit 0

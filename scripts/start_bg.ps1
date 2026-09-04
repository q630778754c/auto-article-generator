$py = 'C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe'
$dir = 'E:\抓取数据\auto-article-generator\backend'
$existing = Get-Process python -ErrorAction SilentlyContinue
if ($existing) { $existing | Stop-Process -Force }
$job = Start-Job -ScriptBlock {
    param($pythonExe, $workDir)
    Set-Location $workDir
    & $pythonExe -m app.main
} -ArgumentList $py, $dir
Start-Sleep -Seconds 8
try {
    $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/health' -UseBasicParsing -TimeoutSec 5
    Write-Output "HEALTH_OK: $($resp.StatusCode)"
} catch {
    Write-Output "HEALTH_FAILED: $($_.Exception.Message)"
}
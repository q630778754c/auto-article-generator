$ErrorActionPreference = "Continue"
$py = "C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe"
$dir = "E:\抓取数据\auto-article-generator\backend"
Set-Location $dir
$job = Start-Job -ScriptBlock {
    Set-Location "E:\抓取数据\auto-article-generator\backend"
    & "C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe" -m app.main
}
Start-Sleep -Seconds 10
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing -TimeoutSec 5
    Write-Output "HEALTH_OK: $($resp.StatusCode)"
} catch {
    Write-Output "HEALTH_FAILED: $($_.Exception.Message)"
}
$output = Receive-Job $job -Keep 2>&1 | Out-String
Write-Output "===JOB OUTPUT (first 4000 chars)==="
if ($output.Length -gt 4000) { Write-Output $output.Substring(0, 4000) } else { Write-Output $output }
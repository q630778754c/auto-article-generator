$content = Get-Content "E:\抓取数据\.codeartsdoer\specs\auto_article_generator_v2\tasks.md" -Raw
$lines = $content -split "`n"
Write-Host ("Total: {0} lines, {1} bytes" -f $lines.Length, $content.Length)
Write-Host "---"
for ($i = 0; $i -lt $lines.Length; $i++) {
    if ($lines[$i] -match "^### ") {
        Write-Host ("Line {0}: {1}" -f ($i + 1), $lines[$i].Substring(0, [Math]::Min(80, $lines[$i].Length)))
    }
}
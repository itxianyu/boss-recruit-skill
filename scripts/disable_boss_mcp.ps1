param(
    [string]$ConfigPath = "$env:USERPROFILE\.codex\config.toml"
)

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    Write-Output "Config file not found: $ConfigPath"
    exit 0
}

$content = Get-Content -LiteralPath $ConfigPath -Raw
$pattern = '(?ms)^\[mcp_servers\.boss-zhipin\].*?(?=^\[mcp_servers\.|\z)'

if ($content -notmatch $pattern) {
    Write-Output "boss-zhipin MCP config not found in $ConfigPath"
    exit 0
}

$updated = [regex]::Replace($content, $pattern, "")
$updated = $updated.TrimEnd() + [Environment]::NewLine

Set-Content -LiteralPath $ConfigPath -Value $updated -Encoding UTF8

Write-Output "Disabled boss-zhipin MCP in $ConfigPath"
Write-Output "Restart Codex to stop the MCP from reopening Boss pages."

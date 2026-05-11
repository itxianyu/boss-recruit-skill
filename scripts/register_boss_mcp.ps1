param(
    [Parameter(Mandatory = $true)]
    [string]$Cookie,

    [Parameter(Mandatory = $true)]
    [string]$Bst,

    [string]$ConfigPath = "$env:USERPROFILE\.codex\config.toml"
)

$configDir = Split-Path -Parent $ConfigPath
if (-not (Test-Path -LiteralPath $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    New-Item -ItemType File -Path $ConfigPath -Force | Out-Null
}

$block = @"
[mcp_servers.boss-zhipin]
command = "npx"
args = ["-y", "mcp-boss-zp"]

[mcp_servers.boss-zhipin.env]
BST = "__BST__"
COOKIE = "__COOKIE__"
"@

$block = $block.Replace("__BST__", $Bst).Replace("__COOKIE__", $Cookie)
$content = Get-Content -LiteralPath $ConfigPath -Raw
$pattern = '(?ms)^\[mcp_servers\.boss-zhipin\].*?(?=^\[mcp_servers\.|\z)'

if ([string]::IsNullOrWhiteSpace($content)) {
    $newContent = $block.Trim() + [Environment]::NewLine
}
elseif ($content -match $pattern) {
    $newContent = [regex]::Replace($content, $pattern, $block.Trim() + [Environment]::NewLine)
}
else {
    $separator = if ($content.EndsWith([Environment]::NewLine)) { "" } else { [Environment]::NewLine + [Environment]::NewLine }
    $newContent = $content + $separator + $block.Trim() + [Environment]::NewLine
}

Set-Content -LiteralPath $ConfigPath -Value $newContent -Encoding UTF8

Write-Output "Updated $ConfigPath with boss-zhipin MCP configuration."
Write-Output "Restart Codex, then run: codex mcp list"

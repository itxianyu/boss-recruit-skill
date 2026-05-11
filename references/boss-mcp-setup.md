# Boss Zhipin MCP Setup

Before using this skill for live Boss Zhipin data, confirm that the local machine has registered and enabled the `boss-zhipin` MCP server.

Also confirm that the machine has a usable Python environment. If Python is missing, install it first by using `scripts/bootstrap_python_env.ps1`.

If the machine does not have `boss-zhipin` registered, do not stop at a missing-MCP error. Help the user register and enable it.

Recommended flow:

1. Ensure Python is installed and install `requirements.txt` dependencies.
2. Ask the user for `COOKIE` and `BST`.
3. Run `scripts/register_boss_mcp.ps1` to write the config.
4. Tell the user to restart the Codex session.
5. After restart, run `codex mcp list` and confirm the server is `enabled`.

Repeated page opening or maintenance redirect:

- If the Boss page keeps opening repeatedly, treat it as MCP failure, not as a normal login flow.
- A screenshot like "当前页面已停止维护，将自动跳转到新页面" is a bad sign. It usually means the third-party MCP landed on an invalid, deprecated, or blocked route.
- Stop retrying.
- Temporarily disable the MCP by running:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\disable_boss_mcp.ps1
```

- Refresh `COOKIE` and `BST`.
- Register the MCP again with `register_boss_mcp.ps1`.
- Restart Codex before testing again.

Python bootstrap example:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_python_env.ps1
```

Script example:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\register_boss_mcp.ps1 `
  -Cookie "<BOSS_COOKIE>" `
  -Bst "<BOSS_BST>"
```

Expected config block:

```toml
[mcp_servers.boss-zhipin]
command = "npx"
args = ["-y", "mcp-boss-zp"]

[mcp_servers.boss-zhipin.env]
BST = "__FILL_BOSS_BST__"
COOKIE = "__FILL_BOSS_COOKIE__"
```

Required values:

- `COOKIE`: Full Boss Zhipin web cookie after login
- `BST`: `bst` value used in Boss requests

How to obtain them:

1. Log in to the Boss Zhipin website in a browser.
2. Open Developer Tools and go to Network.
3. Refresh the page or run a job search.
4. Find a request to a Boss endpoint.
5. Copy the `Cookie` header.
6. Find the `bst` value in request headers or parameters.

Manual fallback:

1. Edit `C:\Users\Administrator\.codex\config.toml`.
2. Add or update the config block above.
3. Restart the Codex session.
4. Run `codex mcp list`.

If live MCP access is still unavailable, the skill can still help with:

- JD analysis
- Resume-to-job matching suggestions
- Outreach and follow-up message drafting
- Recruiting screening rubric design

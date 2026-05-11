# Boss直聘 MCP 接入

使用这个 skill 之前，先确认本机已经注册并启用 `boss-zhipin` MCP server。

当前约定配置：

```toml
[mcp_servers.boss-zhipin]
command = "npx"
args = ["-y", "mcp-boss-zp"]

[mcp_servers.boss-zhipin.env]
BST = "__FILL_BOSS_BST__"
COOKIE = "__FILL_BOSS_COOKIE__"
```

必填环境变量：

- `COOKIE`：Boss直聘网页端登录后的整段 Cookie
- `BST`：Boss直聘请求中使用的 `bst` 值

获取方式：

1. 在浏览器登录 Boss直聘网页端。
2. 打开开发者工具的 Network。
3. 刷新页面或执行一次职位搜索。
4. 找到发往 Boss 相关接口的请求。
5. 从请求头复制 `Cookie`。
6. 从请求参数或请求头中找到 `bst`。

完成后：

1. 编辑 `C:\Users\Administrator\.codex\config.toml`。
2. 替换占位符为真实值。
3. 重启 Codex 会话。
4. 运行 `codex mcp list` 确认服务仍为 `enabled`。

如果 MCP 未连通，这个 skill 仍可用于：

- 岗位 JD 分析
- 简历与岗位匹配建议
- 招呼语和跟进消息撰写
- 招聘筛选规则设计

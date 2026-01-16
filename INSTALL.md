# 快速安装

## 一条命令安装

```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/facai-portfolio-mcp/main/install.sh | bash
```

如果需要使用自定义仓库地址，设置环境变量：

```bash
REPO_URL=https://your-repo-url.git curl -fsSL https://raw.githubusercontent.com/yourusername/facai-portfolio-mcp/main/install.sh | bash
```

## 安装位置

- 安装目录：`~/.facai_mcp`
- 虚拟环境：`~/.facai_mcp/.venv`
- 配置文件：`~/.facai_mcp/data/portfolio.yaml`

## 自动配置

安装完成后，脚本会询问是否自动添加到 Claude Desktop 配置。如果选择是，会自动合并配置。

## 手动配置

如果选择不自动配置，请手动添加以下内容到 Claude Desktop 配置文件：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "portfolio": {
      "command": "/Users/YOUR_USERNAME/.facai_mcp/.venv/bin/portfolio-mcp",
      "env": {
        "PORTFOLIO_FILE": "/Users/YOUR_USERNAME/.facai_mcp/data/portfolio.yaml",
        "REFRESH_INTERVAL_SECONDS": "900",
        "PRICE_TTL_SECONDS": "300",
        "PORTFOLIO_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

请替换 `YOUR_USERNAME` 为你的实际用户名。

## 下一步

1. 编辑持仓配置：`~/.facai_mcp/data/portfolio.yaml`
2. 重启 Claude Desktop
3. 在 Claude 中使用 MCP 工具管理投资组合

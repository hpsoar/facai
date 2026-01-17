# Facai Portfolio MCP

This repository contains a simple Model Context Protocol (MCP) server that lets you maintain
manual holdings, refresh live prices via the yfinance SDK, and expose the resulting portfolio data to
AI agents. You keep full control of positions by editing a YAML file, while the MCP server handles
price polling, PnL calculations, and structured responses. Multiple named portfolios are supported,
so你 can view单个组合 or aggregated totals on demand,并通过 MCP 工具直接增删改资产。

## Features
- Manual holdings file (`data/portfolio.yaml`) with multiple named portfolios.
- Background price refresh with a configurable interval and TTL-based caching.
- Tools/resources for both combined totals and individual portfolio breakdowns.
- Resources so agents can quickly pull a digestible snapshot without running tools first.
- Built with Python and the `mcp` reference SDK so it runs anywhere with basic deps.

## Quick Start
1. **Create a virtual environment** (optional but recommended)
   ```bash
   uv venv .venv && source .venv/bin/activate
   ```
   You can use any environment manager (venv, conda, etc.).
2. **Install dependencies**
   ```bash
   pip install -e .
   ```
3. **Copy and edit the sample portfolio**
   ```bash
   cp data/sample_portfolio.yaml data/portfolio.yaml
   ```
   Adjust the portfolios/holdings with your tickers, quantities, and cost basis data. Symbols follow
   the Yahoo Finance/yfinance format (e.g., `AAPL`, `0700.HK`, `600519.SS`, `000001.SZ`).
4. **Run the MCP server**
    ```bash
    facai-mcp
    ```
   The binary speaks MCP over stdio, so point your AI client to the script. Use env vars to tweak
   behavior:
   - `PORTFOLIO_FILE`: path to the YAML holdings file (default `data/portfolio.yaml`).
   - `REFRESH_INTERVAL_SECONDS`: background refresh cadence (default 900 seconds).
   - `PRICE_TTL_SECONDS`: cache lifetime per symbol (default 300 seconds).
   - `YF_PROXY`: optional HTTPS proxy passed to yfinance (leave unset/empty to disable).
   - `YF_MAX_RETRIES`: how many times to retry yfinance quote requests when 429/503 occurs (default 2).
   - `PORTFOLIO_LOG_FILE`: where to write server logs (default `logs/portfolio-mcp.log`).
   - `PORTFOLIO_LOG_LEVEL`: logging level (default `INFO`).

## Claude Desktop 配置

### 1. 确保服务器已安装

```bash
# 在项目目录中
pip install -e .

# 验证安装
which facai-mcp  # 或 python -m app.__main__
```

### 2. 配置 Claude Desktop

**macOS**: 编辑配置文件
```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows**: 编辑配置文件
```bash
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux**: 编辑配置文件
```bash
~/.config/Claude/claude_desktop_config.json
```

### 3. 添加 MCP 服务器配置

```json
{
  "mcpServers": {
    "facai": {
      "command": "/path/to/your/venv/bin/facai-mcp",
      "env": {
        "PORTFOLIO_FILE": "/path/to/your/data/portfolio.yaml",
        "REFRESH_INTERVAL_SECONDS": "900",
        "PRICE_TTL_SECONDS": "300",
        "PORTFOLIO_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

请将 `/path/to/your/venv` 替换为你的虚拟环境路径，将 `/path/to/your/data` 替换为你的项目路径。

### 4. 创建初始配置文件

```bash
cp data/sample_portfolio.yaml data/portfolio.yaml
```

### 5. 重启 Claude Desktop

配置完成后重启，Claude 会自动加载 MCP 服务器。

### 6. 使用示例

在 Claude 中可直接调用工具:
- `list_portfolios()` - 列出所有组合
- `get_summary()` - 查看总览
- `refresh_prices()` - 刷新价格
- `search_symbols("茅台")` - 搜索股票代码
- `add_holding(...)` - 添加持仓

### 环境变量说明

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `PORTFOLIO_FILE` | `data/portfolio.yaml` | 持仓 YAML 文件路径 |
| `REFRESH_INTERVAL_SECONDS` | `900` | 后台刷新间隔(秒),设为 0 禁用自动刷新 |
| `PRICE_TTL_SECONDS` | `300` | 价格缓存过期时间(秒) |
| `YF_PROXY` | - | yfinance 代理 URL(可选) |
| `YF_MAX_RETRIES` | `2` | 429/503 错误重试次数 |
| `PORTFOLIO_LOG_FILE` | `logs/facai-mcp.log` | 日志文件路径 |
| `PORTFOLIO_LOG_LEVEL` | `INFO` | 日志级别 |

## MCP Surfaces
- **Resource** `portfolio://portfolios` — list portfolio ids, names, and holding counts.
- **Resource** `portfolio://summary` — combined valuation totals with last refresh time.
- **Resource** `portfolio://summary/{portfolio_id}` — summary for a specific portfolio
  (`portfolio_id` from the YAML file).
- **Resource** `portfolio://positions` — aggregated holdings with metadata.
- **Resource** `portfolio://positions/{portfolio_id}` — holdings for a single portfolio.
- **Tool** `list_portfolios` — same data as the resource, but invokable on demand.
- **Tool** `refresh_prices` — forces an immediate price pull for all tracked symbols.
- **Tool** `get_positions(symbol?, portfolio_id?)` — filter holdings by ticker, portfolio, or both.
- **Tool** `reload_portfolio` — re-read the YAML file if you changed it on disk.
- **Tool** `get_summary(portfolio_id?)` — structured summary for combined or per-portfolio views.
- **Tool** `search_symbols(query, region?, limit?)` — symbol search with Chinese name support.
- **Tool** `create_portfolio` / `update_portfolio` / `delete_portfolio(force?)` — manage portfolio
  containers.
- **Tool** `add_holding` / `remove_holding` / `update_holding` — edit holdings (supports fuzzy search
  via `search_query`).

The CLI defaults to stdio transport, but you can switch transports when needed:

```bash
facai-mcp --transport streamable-http --host 0.0.0.0 --port 9000
```

## Data File Format
```yaml
base_currency: CNY
portfolios:
  - id: cn-growth
    name: A股成长
    notes: 核心消费与白酒
    holdings:
      - id: maotai
        broker: a-stock
        symbol: 600519.SS
        name: 贵州茅台
        quantity: 20
        cost_basis: 1680.5
        currency: CNY
        category: consumer
  - id: hk-tech
    name: 港股互联网
    holdings:
      - id: tencent
        broker: hk-stock
        symbol: 0700.HK
        name: 腾讯控股
        quantity: 150
        cost_basis: 305.0
        currency: HKD
        category: tech
```

Fields beyond `symbol`, `quantity`, and `cost_basis` are optional and used only for display. You can
add your own metadata, and the MCP will surface it untouched so agents can reason about tags or
scenarios. If you prefer the legacy single-portfolio format, you may omit the `portfolios` section
and keep a top-level `holdings:` list—the server will treat it as a default portfolio (`id:
default`).

## Logging
- Logs are written to `logs/facai-mcp.log` by default; override with `PORTFOLIO_LOG_FILE`.
- Adjust verbosity via `PORTFOLIO_LOG_LEVEL` (e.g., `DEBUG` for detailed traces).
- Each resource/tool invocation records concise entries (portfolio id, holdings count, key params) so
  you can audit AI actions without reading stdout.

## Managing Portfolios via MCP
- **Create** a portfolio: `create_portfolio(portfolio_id="hk-income", name="港股收息")`
- **List** all portfolios: `list_portfolios`
- **Add** a holding with fuzzy search: `add_holding(portfolio_id="hk-income", search_query="中电控股", quantity=100, cost_basis=49.5, currency="HKD")`
- **Remove** a holding: `remove_holding(portfolio_id="hk-income", holding_key="clp")` (matches id or symbol)
- **Update** a holding's quantity/cost: `update_holding(portfolio_id="hk-income", holding_id="clp", quantity=150)`
- **Delete** a portfolio: `delete_portfolio(portfolio_id="hk-income", force=true)` (force required when non-empty)

这些操作会自动落盘到 `PORTFOLIO_FILE` 并刷新行情缓存，Claude/CLI 即可立即使用最新配置。

## Symbol Search

The `search_symbols` tool supports multiple search methods:

### Chinese Stock Names (NEW)
Search A-shares and HK stocks by Chinese company names:
- `search_symbols(query="茅台")` → Returns `600519.SS` (贵州茅台)
- `search_symbols(query="腾讯")` → Returns `00700.HK` (腾讯控股)
- `search_symbols(query="阿里巴巴")` → Returns `09988.HK` (阿里巴巴-W)

This uses AKShare and East Money APIs to find Chinese stocks by name, then returns results in yfinance-compatible format.

### Stock Codes
Search by ticker codes (most precise):
- `600519.SS` - Shanghai A-shares
- `000963.SZ` - Shenzhen A-shares
- `0700.HK` - Hong Kong stocks
- `AAPL` - US stocks

### English Names
Search by English company names:
- `search_symbols(query="Apple")` → Returns `AAPL`
- `search_symbols(query="tencent")` → Returns `0700.HK`
- `search_symbols(query="moutai")` → Returns `600519.SS`

## Scheduling Refreshes
The server already refreshes prices in the background as long as it stays running. If you only want
updates occasionally, you can disable the interval (`REFRESH_INTERVAL_SECONDS=0`) and instead run the
`refresh_prices` tool from the AI client whenever needed.

For unattended operation, keep the MCP in a tmux session or systemd service so it continually updates
prices and responds instantly when your AI requests the summary resource.

## Security Notes
- The holdings file never leaves your machine unless you share it. MCP responses include only the
data you request.
- No trading credentials or brokerage APIs are involved; prices come from public quote endpoints.
- If you later integrate with real broker APIs, treat credentials carefully and extend the MCP with
  dedicated secrets management.

## Next Steps
- Add multiple price providers (e.g., Alpha Vantage) and failover logic.
- Track cash, crypto, or funds by adding new loader modules (or additional portfolio entries).
- Log refresh history to a SQLite DB for auditing.

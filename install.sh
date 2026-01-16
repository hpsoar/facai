#!/usr/bin/env bash
set -e

INSTALL_DIR="$HOME/.facai_mcp"
VENV_NAME=".venv"
REPO_URL="${REPO_URL:-https://github.com/hpsoar/facai.git}"

if [[ "$OSTYPE" == "darwin"* ]]; then
    CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    CLAUDE_CONFIG_DIR="$APPDATA/Claude"
else
    echo "不支持的操作系统: $OSTYPE"
    exit 1
fi

echo "========================================"
echo "Facai Portfolio MCP 安装脚本"
echo "========================================"
echo ""

echo "步骤 1: 克隆代码仓库..."
if [ -d "$INSTALL_DIR" ]; then
    echo "目录已存在: $INSTALL_DIR"
    read -p "是否删除并重新克隆? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
        echo "已删除旧目录"
    else
        echo "跳过克隆步骤"
    fi
fi

if [ ! -d "$INSTALL_DIR" ]; then
    echo "克隆仓库: $REPO_URL"
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

echo ""
echo "步骤 2: 创建虚拟环境..."
VENV_DIR="$INSTALL_DIR/$VENV_NAME"
if [ -d "$VENV_DIR" ]; then
    echo "虚拟环境已存在: $VENV_DIR"
else
    python3 -m venv "$VENV_DIR"
    echo "虚拟环境创建成功"
fi

echo ""
echo "步骤 3: 安装依赖..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -e "$INSTALL_DIR" -q
echo "依赖安装完成"

echo ""
echo "步骤 4: 创建示例配置文件..."
PORTFOLIO_FILE="$INSTALL_DIR/data/portfolio.yaml"
if [ ! -f "$PORTFOLIO_FILE" ]; then
    cp "$INSTALL_DIR/data/sample_portfolio.yaml" "$PORTFOLIO_FILE"
    echo "示例配置已创建: $PORTFOLIO_FILE"
else
    echo "配置文件已存在: $PORTFOLIO_FILE"
fi

echo ""
echo "步骤 5: 生成 MCP 配置..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    PORTFOLIO_MCP_CMD=$(echo "$INSTALL_DIR/$VENV_NAME/Scripts/portfolio-mcp.exe" | sed 's|/|\\|g')
else
    PORTFOLIO_MCP_CMD="$INSTALL_DIR/$VENV_NAME/bin/portfolio-mcp"
fi

MCP_CONFIG=$(cat <<EOF
{
  "mcpServers": {
    "portfolio": {
      "command": "$PORTFOLIO_MCP_CMD",
      "env": {
        "PORTFOLIO_FILE": "$PORTFOLIO_FILE",
        "REFRESH_INTERVAL_SECONDS": "900",
        "PRICE_TTL_SECONDS": "300",
        "PORTFOLIO_LOG_LEVEL": "INFO"
      }
    }
  }
}
EOF
)

echo "$MCP_CONFIG" > "$INSTALL_DIR/claude_mcp_config.json"
echo "配置已生成: $INSTALL_DIR/claude_mcp_config.json"

echo ""
echo "步骤 6: 验证安装..."
if "$VENV_DIR/bin/python" -m portfolio_mcp.server --help > /dev/null 2>&1; then
    echo "✓ MCP 服务器安装成功"
else
    echo "✗ MCP 服务器验证失败"
    exit 1
fi

echo ""
echo "========================================"
echo "安装完成!"
echo "========================================"
echo ""
echo "安装目录: $INSTALL_DIR"
echo "虚拟环境: $VENV_DIR"
echo "配置文件: $INSTALL_DIR/claude_mcp_config.json"
echo ""

echo "请将以下配置添加到 Claude Desktop:"
echo "  配置文件路径: $CLAUDE_CONFIG_DIR/claude_desktop_config.json"
echo ""
echo "配置内容:"
echo "$MCP_CONFIG"
echo ""

echo "下一步:"
echo "  1. 编辑配置文件: $PORTFOLIO_FILE"
echo "  2. 将上述配置添加到 Claude Desktop"
echo "  3. 重启 Claude Desktop"
echo ""

read -p "是否自动添加到 Claude Desktop 配置? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    mkdir -p "$CLAUDE_CONFIG_DIR"
    CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

    if [ -f "$CONFIG_FILE" ]; then
        if command -v jq &> /dev/null; then
            TEMP_FILE=$(mktemp)
            jq --argjson new "$(echo "$MCP_CONFIG")" '.mcpServers += $new.mcpServers' "$CONFIG_FILE" > "$TEMP_FILE"
            mv "$TEMP_FILE" "$CONFIG_FILE"
        else
            echo "警告: 未找到 jq，请手动合并配置"
            echo "配置内容已保存到: $INSTALL_DIR/claude_mcp_config.json"
            exit 0
        fi
    else
        echo "$MCP_CONFIG" > "$CONFIG_FILE"
    fi
    echo "✓ 配置已添加到: $CONFIG_FILE"
else
    echo "跳过自动配置，请手动添加"
fi

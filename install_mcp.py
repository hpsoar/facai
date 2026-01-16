#!/usr/bin/env python3
"""Facai Portfolio MCP 安装脚本。

使用方法:
    python install_mcp.py [选项]

选项:
    --install-dir DIR     安装目录 (默认: ~/facai-portfolio-mcp)
    --venv-name NAME      虚拟环境名称 (默认: .venv)
    --config-out FILE     配置文件输出路径 (默认: ./claude_mcp_config.json)
    --skip-deps           跳过依赖安装
    --help                显示帮助信息
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run_command(
    cmd: list[str], cwd: Path | None = None, check: bool = True
) -> subprocess.CompletedProcess:
    """运行命令并返回结果。"""
    print(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)
    return result


def clone_repo(repo_url: str, install_dir: Path) -> None:
    """克隆代码仓库。"""
    if install_dir.exists():
        print(f"目录已存在: {install_dir}")
        response = input("是否删除并重新克隆? [y/N]: ")
        if response.lower() == "y":
            import shutil

            shutil.rmtree(install_dir)
            print(f"已删除: {install_dir}")
        else:
            print("跳过克隆步骤")
            return

    print(f"克隆仓库到: {install_dir}")
    run_command(["git", "clone", repo_url, str(install_dir)])


def setup_venv(install_dir: Path, venv_name: str = ".venv") -> Path:
    """创建虚拟环境并返回 Python 可执行文件路径。"""
    venv_dir = install_dir / venv_name
    python_path = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

    if python_path.exists():
        print(f"虚拟环境已存在: {venv_dir}")
        response = input("是否重新创建? [y/N]: ")
        if response.lower() == "y":
            import shutil

            shutil.rmtree(venv_dir)
            print(f"已删除: {venv_dir}")
        else:
            print("跳过虚拟环境创建")
            return python_path

    print(f"创建虚拟环境: {venv_dir}")
    run_command([sys.executable, "-m", "venv", str(venv_dir)])
    return python_path


def install_deps(python_path: Path, install_dir: Path) -> None:
    """安装项目依赖。"""
    print("安装依赖...")
    run_command([str(python_path), "-m", "pip", "install", "--upgrade", "pip"])
    run_command([str(python_path), "-m", "pip", "install", "-e", str(install_dir)])


def create_sample_portfolio(install_dir: Path) -> Path:
    """创建示例配置文件。"""
    sample_file = install_dir / "data" / "sample_portfolio.yaml"
    portfolio_file = install_dir / "data" / "portfolio.yaml"

    if not portfolio_file.exists() and sample_file.exists():
        import shutil

        shutil.copy(sample_file, portfolio_file)
        print(f"已创建示例配置: {portfolio_file}")

    return portfolio_file


def generate_mcp_config(
    install_dir: Path,
    venv_name: str = ".venv",
    portfolio_file: Path | None = None,
) -> dict:
    """生成 MCP 配置。"""
    if sys.platform == "win32":
        command = str(install_dir / venv_name / "Scripts" / "portfolio-mcp.exe")
    else:
        command = str(install_dir / venv_name / "bin" / "portfolio-mcp")

    if portfolio_file is None:
        portfolio_file = install_dir / "data" / "portfolio.yaml"

    config = {
        "mcpServers": {
            "portfolio": {
                "command": command,
                "env": {
                    "PORTFOLIO_FILE": str(portfolio_file),
                    "REFRESH_INTERVAL_SECONDS": "900",
                    "PRICE_TTL_SECONDS": "300",
                    "PORTFOLIO_LOG_LEVEL": "INFO",
                },
            }
        }
    }

    return config


def save_config(config: dict, output_path: Path) -> None:
    """保存配置到文件。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"\n配置已保存到: {output_path}")
    print(f"\n请将以下内容添加到 Claude Desktop 配置文件中:")
    if sys.platform == "darwin":
        print("  ~/Library/Application Support/Claude/claude_desktop_config.json")
    elif sys.platform == "win32":
        print("  %APPDATA%\\Claude\\claude_desktop_config.json")
    else:
        print("  ~/.config/Claude/claude_desktop_config.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Facai Portfolio MCP 安装脚本")
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=Path.home() / "facai-portfolio-mcp",
        help="安装目录 (默认: ~/facai-portfolio-mcp)",
    )
    parser.add_argument(
        "--venv-name",
        default=".venv",
        help="虚拟环境名称 (默认: .venv)",
    )
    parser.add_argument(
        "--config-out",
        type=Path,
        default=Path.cwd() / "claude_mcp_config.json",
        help="配置文件输出路径 (默认: ./claude_mcp_config.json)",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="跳过依赖安装",
    )
    parser.add_argument(
        "--repo-url",
        default="https://github.com/hpsoar/facai.git",
        help="Git 仓库 URL",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Facai Portfolio MCP 安装脚本")
    print("=" * 60)

    print("\n步骤 1: 克隆代码仓库...")
    clone_repo(args.repo_url, args.install_dir)

    print("\n步骤 2: 创建虚拟环境...")
    python_path = setup_venv(args.install_dir, args.venv_name)

    if not args.skip_deps:
        print("\n步骤 3: 安装依赖...")
        install_deps(python_path, args.install_dir)
    else:
        print("\n步骤 3: 跳过依赖安装")

    print("\n步骤 4: 创建示例配置文件...")
    portfolio_file = create_sample_portfolio(args.install_dir)

    print("\n步骤 5: 生成 MCP 配置...")
    config = generate_mcp_config(args.install_dir, args.venv_name, portfolio_file)
    save_config(config, args.config_out)

    print("\n步骤 6: 验证安装...")
    try:
        result = run_command(
            [str(python_path), "-m", "portfolio_mcp.server", "--help"],
            cwd=args.install_dir,
        )
        print("✓ MCP 服务器安装成功")
    except subprocess.CalledProcessError:
        print("✗ MCP 服务器验证失败")
        return 1

    print("\n" + "=" * 60)
    print("安装完成!")
    print("=" * 60)
    print(f"\n安装目录: {args.install_dir}")
    print(f"虚拟环境: {args.install_dir / args.venv_name}")
    print(f"配置文件: {args.config_out}")
    print(f"\n下一步:")
    print("  1. 编辑配置文件 data/portfolio.yaml 添加你的持仓")
    print("  2. 将 MCP 配置添加到 Claude Desktop")
    print("  3. 重启 Claude Desktop")

    return 0


if __name__ == "__main__":
    sys.exit(main())

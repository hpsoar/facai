"""Test configuration and fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import PortfolioApp
from app.config import Settings


@pytest.fixture
def sample_portfolio_path(tmp_path: Path) -> Path:
    """Create a sample portfolio file for testing."""
    portfolio_file = tmp_path / "portfolio.yaml"
    portfolio_file.write_text(
        """base_currency: CNY
portfolios:
  - id: cn-growth
    name: A股成长
    notes: 核心消费与白酒
    holdings:
      - id: maotai
        symbol: 600519.SS
        name: 贵州茅台
        quantity: 20.0
        cost_basis: 1680.5
        currency: CNY
        broker: a-stock
        category: consumer
  - id: hk-tech
    name: 港股互联网
    holdings:
      - id: tencent
        symbol: 0700.HK
        name: 腾讯控股
        quantity: 150.0
        cost_basis: 305.0
        currency: HKD
        broker: hk-stock
        category: tech
"""
    )
    return portfolio_file


@pytest.fixture
def test_settings(sample_portfolio_path: Path) -> Settings:
    """Create test settings with a temporary portfolio file."""
    return Settings(
        portfolio_file=sample_portfolio_path,
        refresh_interval_seconds=0,
        price_ttl_seconds=300,
    )


@pytest.fixture
async def app(test_settings: Settings) -> PortfolioApp:
    """Create and start a PortfolioApp instance for testing."""
    app = PortfolioApp(test_settings)
    await app.start()
    yield app
    await app.stop()

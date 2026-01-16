"""Typed models for holdings and valuations."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Holding(BaseModel):
    symbol: str = Field(..., description="Yahoo Finance / yfinance style ticker symbol")
    quantity: float = Field(..., ge=0)
    cost_basis: float = Field(..., ge=0, description="Per-share cost basis in holding currency")
    currency: Optional[str] = Field(None, description="Currency code of the cost basis")
    id: Optional[str] = Field(None, description="User defined unique identifier")
    name: Optional[str] = None
    broker: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None

    def book_value(self) -> float:
        return self.quantity * self.cost_basis


class PortfolioFile(BaseModel):
    base_currency: str = Field("USD", description="Primary reporting currency")
    holdings: List[Holding] = Field(default_factory=list)
    portfolios: List["PortfolioDefinition"] = Field(default_factory=list)


class PriceQuote(BaseModel):
    symbol: str
    currency: Optional[str] = None
    price: Optional[float] = None
    fetched_at: Optional[datetime] = None
    provider: str = "yfinance"


class HoldingSnapshot(BaseModel):
    holding: Holding
    quote: PriceQuote
    market_value: Optional[float] = None
    gain_abs: Optional[float] = None
    gain_pct: Optional[float] = None
    portfolio_id: Optional[str] = Field(
        None, description="Portfolio identifier that owns this holding"
    )
    portfolio_name: Optional[str] = None


class PortfolioSummary(BaseModel):
    base_currency: str
    portfolio_id: str
    portfolio_name: Optional[str] = None
    total_book: float
    total_market: float
    total_gain: float
    total_gain_pct: float
    refreshed_at: datetime
    symbols: List[str]
    holding_count: int


class PortfolioDefinition(BaseModel):
    id: str = Field(..., description="Unique portfolio identifier")
    name: Optional[str] = Field(None, description="Friendly portfolio name")
    notes: Optional[str] = None
    holdings: List[Holding] = Field(default_factory=list)


PortfolioFile.model_rebuild()

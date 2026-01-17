"""Portfolio data loading and aggregation helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import yaml

from .models import (
    Holding,
    HoldingSnapshot,
    PortfolioDefinition,
    PortfolioFile,
    PortfolioSummary,
    PriceQuote,
)

DEFAULT_PORTFOLIO_ID = "default"
AGGREGATE_PORTFOLIO_ID = "all"


class PortfolioStore:
    """Loads holdings from disk and computes derived views."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._data = PortfolioFile(base_currency="USD", holdings=[])
        self._portfolios: Dict[str, PortfolioDefinition] = {}
        self.reload()

    @property
    def data(self) -> PortfolioFile:
        return self._data

    def reload(self) -> PortfolioFile:
        if not self.file_path.exists():
            self._data = PortfolioFile(base_currency="USD", holdings=[])
            return self._data
        raw = yaml.safe_load(self.file_path.read_text()) or {}
        self._data = PortfolioFile.model_validate(raw)
        self._portfolios = self._build_portfolio_map(self._data)
        return self._data

    def save(self) -> None:
        serialized = yaml.safe_dump(
            self._data.model_dump(mode="python"),
            sort_keys=False,
            allow_unicode=True,
        )
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(serialized)

    def _refresh_cache(self) -> None:
        self._portfolios = self._build_portfolio_map(self._data)

    def _ensure_portfolios_initialized(self) -> None:
        if self._data.portfolios:
            return
        default_holdings = list(self._data.holdings)
        default_portfolio = PortfolioDefinition(
            id=DEFAULT_PORTFOLIO_ID,
            name="Default Portfolio",
            holdings=default_holdings,
        )
        self._data.portfolios = [default_portfolio]
        self._data.holdings = []
        self._refresh_cache()

    def _build_portfolio_map(self, data: PortfolioFile) -> Dict[str, PortfolioDefinition]:
        portfolios: Dict[str, PortfolioDefinition] = {}
        if data.portfolios:
            for definition in data.portfolios:
                if not definition.id:
                    raise ValueError("Each portfolio entry must have an id")
                if definition.id in portfolios:
                    raise ValueError(f"Duplicate portfolio id detected: {definition.id}")
                portfolios[definition.id] = definition
        elif data.holdings:
            portfolios[DEFAULT_PORTFOLIO_ID] = PortfolioDefinition(
                id=DEFAULT_PORTFOLIO_ID,
                name="Default Portfolio",
                holdings=data.holdings,
            )
        else:
            portfolios[DEFAULT_PORTFOLIO_ID] = PortfolioDefinition(
                id=DEFAULT_PORTFOLIO_ID,
                name="Default Portfolio",
                holdings=[],
            )
        return portfolios

    def portfolio_ids(self) -> List[str]:
        return sorted(self._portfolios.keys())

    def portfolios(self) -> Dict[str, PortfolioDefinition]:
        return dict(self._portfolios)

    def symbols(self) -> List[str]:
        symbols = {holding.symbol for _, holding in self._iter_holdings(None)}
        return sorted(symbols)

    def _iter_holdings(
        self, portfolio_id: Optional[str]
    ) -> Iterable[tuple[PortfolioDefinition, Holding]]:
        if portfolio_id is None:
            for definition in self._portfolios.values():
                for holding in definition.holdings:
                    yield definition, holding
            return
        if portfolio_id not in self._portfolios:
            raise ValueError(f"Unknown portfolio id: {portfolio_id}")
        definition = self._portfolios[portfolio_id]
        for holding in definition.holdings:
            yield definition, holding

    def snapshots(
        self, quotes: Dict[str, PriceQuote], portfolio_id: Optional[str] = None
    ) -> List[HoldingSnapshot]:
        snapshots: List[HoldingSnapshot] = []
        for definition, holding in self._iter_holdings(portfolio_id):
            quote = quotes.get(holding.symbol.upper()) or PriceQuote(symbol=holding.symbol)
            market_value = holding.quantity * quote.price if quote.price is not None else None
            gain_abs = market_value - holding.book_value() if market_value is not None else None
            gain_pct = (
                (market_value / holding.book_value()) - 1
                if market_value is not None and holding.book_value() > 0
                else None
            )
            snapshots.append(
                HoldingSnapshot(
                    holding=holding,
                    quote=quote,
                    market_value=market_value,
                    gain_abs=gain_abs,
                    gain_pct=gain_pct,
                    portfolio_id=definition.id,
                    portfolio_name=definition.name,
                )
            )
        return snapshots

    def summary(
        self, quotes: Dict[str, PriceQuote], portfolio_id: Optional[str] = None
    ) -> PortfolioSummary:
        snapshots = self.snapshots(quotes, portfolio_id)
        total_book = sum(h.holding.book_value() for h in snapshots)
        total_market = sum((h.market_value or 0.0) for h in snapshots)
        total_gain = total_market - total_book
        total_gain_pct = (total_market / total_book - 1) if total_book else 0.0
        refreshed_at = _latest_timestamp(quotes.values())
        if portfolio_id and portfolio_id not in self._portfolios:
            raise ValueError(f"Unknown portfolio id: {portfolio_id}")
        if portfolio_id:
            definition = self._portfolios[portfolio_id]
            pid = definition.id
            pname = definition.name
        else:
            pid = AGGREGATE_PORTFOLIO_ID
            pname = "All Portfolios"
        symbols = sorted({snap.holding.symbol for snap in snapshots})
        return PortfolioSummary(
            base_currency=self._data.base_currency,
            portfolio_id=pid,
            portfolio_name=pname,
            total_book=round(total_book, 2),
            total_market=round(total_market, 2),
            total_gain=round(total_gain, 2),
            total_gain_pct=round(total_gain_pct, 4),
            refreshed_at=refreshed_at,
            symbols=symbols,
            holding_count=len(snapshots),
        )

    def portfolio_metadata(self) -> List[Dict[str, Optional[str]]]:
        items: List[Dict[str, Optional[str]]] = []
        for definition in self._portfolios.values():
            items.append(
                {
                    "id": definition.id,
                    "name": definition.name,
                    "holding_count": len(definition.holdings),
                }
            )
        return items

    def create_portfolio(
        self, portfolio_id: str, name: Optional[str], notes: Optional[str]
    ) -> PortfolioDefinition:
        self._ensure_portfolios_initialized()
        if not portfolio_id:
            raise ValueError("portfolio_id is required")
        if portfolio_id in self._portfolios:
            raise ValueError(f"Portfolio {portfolio_id} already exists")
        definition = PortfolioDefinition(id=portfolio_id, name=name, notes=notes, holdings=[])
        self._data.portfolios.append(definition)
        self.save()
        self._refresh_cache()
        return definition

    def update_portfolio(
        self,
        portfolio_id: str,
        *,
        name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PortfolioDefinition:
        self._ensure_portfolios_initialized()
        if portfolio_id not in self._portfolios:
            raise ValueError(f"Portfolio {portfolio_id} does not exist")
        definition = self._portfolios[portfolio_id]
        if name is not None:
            definition.name = name
        if notes is not None:
            definition.notes = notes
        self.save()
        self._refresh_cache()
        return definition

    def delete_portfolio(self, portfolio_id: str, *, force: bool = False) -> PortfolioDefinition:
        self._ensure_portfolios_initialized()
        if portfolio_id not in self._portfolios:
            raise ValueError(f"Portfolio {portfolio_id} does not exist")
        if len(self._portfolios) <= 1:
            raise ValueError("Cannot delete the last portfolio")
        definition = self._portfolios[portfolio_id]
        if definition.holdings and not force:
            raise ValueError("Portfolio is not empty; set force=true to delete anyway")
        self._data.portfolios = [p for p in self._data.portfolios if p.id != portfolio_id]
        self.save()
        self._refresh_cache()
        return definition

    def _generate_holding_id(self, portfolio: PortfolioDefinition, symbol: str) -> str:
        base = symbol.lower().replace(".", "-")
        candidate = base
        suffix = 1
        existing_ids = {holding.id for holding in portfolio.holdings if holding.id}
        while not candidate or candidate in existing_ids:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    def add_holding(self, portfolio_id: str, holding: Holding) -> Holding:
        self._ensure_portfolios_initialized()
        if portfolio_id not in self._portfolios:
            raise ValueError(f"Portfolio {portfolio_id} does not exist")
        portfolio = self._portfolios[portfolio_id]
        if not holding.id:
            holding.id = self._generate_holding_id(portfolio, holding.symbol)
        elif any(existing.id == holding.id for existing in portfolio.holdings):
            raise ValueError(f"Holding id {holding.id} already exists in portfolio {portfolio_id}")
        portfolio.holdings.append(holding)
        self.save()
        self._refresh_cache()
        return holding

    def _find_holding_index(self, portfolio: PortfolioDefinition, key: str) -> int:
        matches = [
            idx
            for idx, holding in enumerate(portfolio.holdings)
            if (holding.id and holding.id == key) or holding.symbol.upper() == key.upper()
        ]
        if not matches:
            raise ValueError(f"Holding '{key}' not found in portfolio {portfolio.id}")
        if len(matches) > 1:
            raise ValueError(
                f"Multiple holdings match '{key}' in portfolio {portfolio.id}; use holding id instead"
            )
        return matches[0]

    def remove_holding(self, portfolio_id: str, holding_key: str) -> Holding:
        self._ensure_portfolios_initialized()
        if portfolio_id not in self._portfolios:
            raise ValueError(f"Portfolio {portfolio_id} does not exist")
        portfolio = self._portfolios[portfolio_id]
        index = self._find_holding_index(portfolio, holding_key)
        holding = portfolio.holdings.pop(index)
        self.save()
        self._refresh_cache()
        return holding

    def update_holding(
        self,
        portfolio_id: str,
        holding_id: str,
        *,
        quantity: Optional[float] = None,
        cost_basis: Optional[float] = None,
        notes: Optional[str] = None,
        broker: Optional[str] = None,
        category: Optional[str] = None,
        name: Optional[str] = None,
        currency: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> Holding:
        self._ensure_portfolios_initialized()
        if portfolio_id not in self._portfolios:
            raise ValueError(f"Portfolio {portfolio_id} does not exist")
        portfolio = self._portfolios[portfolio_id]
        holding = next((h for h in portfolio.holdings if h.id == holding_id), None)
        if holding is None:
            raise ValueError(f"Holding id {holding_id} not found in portfolio {portfolio_id}")
        if quantity is not None:
            holding.quantity = quantity
        if cost_basis is not None:
            holding.cost_basis = cost_basis
        if notes is not None:
            holding.notes = notes
        if broker is not None:
            holding.broker = broker
        if category is not None:
            holding.category = category
        if name is not None:
            holding.name = name
        if currency is not None:
            holding.currency = currency
        if symbol is not None:
            holding.symbol = symbol
        self.save()
        self._refresh_cache()
        return holding


def _latest_timestamp(quotes: Iterable[PriceQuote]) -> datetime:
    ts = [quote.fetched_at for quote in quotes if quote.fetched_at]
    if not ts:
        return datetime.now(timezone.utc)
    return max(ts)

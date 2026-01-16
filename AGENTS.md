# Repository Guidelines

## Project Structure & Module Organization
- `portfolio_mcp/` houses the MCP server code: `app.py` coordinates storage/pricing/scheduler; `pricing.py` handles yfinance-backed quotes with TTL cache; `portfolio.py` defines valuation logic and YAML persistence; `scheduler.py` keeps prices warm. Keep new runtime modules inside this package.
- `data/portfolio.yaml` (or `PORTFOLIO_FILE` env var) stores holdings; `data/sample_portfolio.yaml` is a template. Treat YAML edits as source-controlled artifacts.
- Tests should be placed under `tests/` directory mirroring the package layout (e.g., `tests/test_pricing.py`, `tests/test_portfolio.py`).

## Build, Test, and Development Commands
- `pip install -e .[dev]` sets up the editable package plus tooling (`ruff`, `pytest`).
- `portfolio-mcp` (or `python -m portfolio_mcp.server`) launches the MCP server with stdio transport; add `--transport streamable-http --host 0.0.0.0 --port 9000` to expose HTTP.
- `pytest` runs the full test suite; `pytest tests/test_pricing.py -v` runs a single test file; `pytest tests/test_pricing.py::test_cache_expiry -v` runs a specific test.
- `ruff check portfolio_mcp` ensures code style compliance; `ruff format portfolio_mcp` auto-formats code.
- Run `ruff check` and `pytest` before committing changes.

## Coding Style & Naming Conventions
- Target Python ≥3.10 with type hints on all function signatures and class attributes.
- Use Pydantic models for structured data (see `models.py`). Prefer dataclasses for simple config objects (see `config.py`).
- Follow Ruff/PEP 8: 4-space indents, 100-character line limit (configured in `pyproject.toml`).
- Modules and files use snake_case; classes are PascalCase; constants use UPPER_SNAKE_CASE.
- Keep loggers module-scoped: `logger = logging.getLogger(__name__)`.
- Use `from __future__ import annotations` at the top of all modules for forward references.
- Import order: standard library → third-party → local modules, separated by blank lines.

## Type Safety & Error Handling
- Never suppress type errors with `# type: ignore` or `Any` without justification.
- Use `Optional[T]` for nullable fields; provide clear error messages in `ValueError`/`RuntimeError`.
- Use Pydantic's `Field(..., ge=0)` for numeric constraints (e.g., `quantity: float = Field(..., ge=0)`).
- Network operations (yfinance calls) should be wrapped with retry logic and exponential backoff (see `pricing.py`).
- Log exceptions at appropriate levels: `logger.exception()` for errors, `logger.warning()` for expected failures.

## Testing Guidelines
- Use `pytest` with descriptive function names: `test_<module>_<behavior>`.
- Group shared fixtures in `tests/conftest.py` (e.g., sample YAML fixtures, mock yfinance tickers).
- Mock external dependencies: use `unittest.mock.patch` for `yfinance.Ticker` to avoid live network calls.
- Load small YAML fixtures from `tests/fixtures/` copies for portfolio math tests.
- Strive for coverage on: PnL calculations, scheduler refresh logic, cache expiry, error handling (proxies/retries), and portfolio CRUD operations.

## Security & Configuration Tips
- Proxy defaults in `portfolio_mcp/proxy.py`; override via `YF_PROXY` env var. Never bake credentials into repo files.
- Audit new MCP tools/resources for least-privilege data exposure—avoid surfacing raw holdings/notes unnecessarily.
- Log files (`PORTFOLIO_LOG_FILE`) may contain sensitive holdings; clean before sharing traces.
- Validate all user inputs in Pydantic models before use.

## Commit & Pull Request Guidelines
- Git history favors short imperative subjects with `MOD:` prefix (e.g., `MOD: add yfinance pricing`).
- Each PR should describe motivation, list command/test evidence (`ruff check`, `pytest`), and link related issues.
- Include CLI output or MCP tool response examples when behavior changes.
- Keep diffs focused; separate drive-by refactors into their own commits for easier review.

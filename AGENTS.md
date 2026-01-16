# Repository Guidelines

## Project Structure & Module Organization
- `portfolio_mcp/` houses the MCP server code: `app.py` wires settings, storage, and pricing; `pricing.py` handles yfinance-backed quotes; `portfolio.py` defines valuation logic; `scheduler.py` keeps prices warm. Keep new runtime modules inside this package.
- `data/portfolio.yaml` (or the path set via `PORTFOLIO_FILE`) stores holdings; `data/sample_portfolio.yaml` is a template. Treat YAML edits as source-controlled artifacts.
- `README.md` documents transports and env vars; update it when you change runtime behavior. Tests are expected under a future `tests/` directory—mirror the package layout when adding them.

## Build, Test, and Development Commands
- `pip install -e .[dev]` sets up the editable package plus tooling (`ruff`, `pytest`).
- `portfolio-mcp` (or `python -m portfolio_mcp.server`) launches the MCP server with stdio transport; add `--transport streamable-http` to expose HTTP.
- `pytest` will execute the suite once tests land; skip if the project still lacks them.
- `ruff check portfolio_mcp` ensures code style remains consistent.

## Coding Style & Naming Conventions
- Target Python ≥3.10 with type hints and Pydantic models; prefer dataclasses or Pydantic for structured data.
- Follow Ruff/PEP 8 defaults: 4-space indents, 100-character lines (configured in `pyproject.toml`).
- Modules and files use snake_case; classes are PascalCase. Keep loggers module-scoped via `logging.getLogger(__name__)`.

## Testing Guidelines
- Use `pytest` with descriptive function names (`test_<module>_<behavior>`). Group shared fixtures in `conftest.py` per package.
- Exercise the price pipeline with mocked `yfinance.Ticker` objects to avoid live network calls. For portfolio math, load small YAML fixtures from `data/` copies.
- Strive for regression coverage on PnL math, scheduler refresh logic, and error handling around proxies/retries.

## Security & Configuration Tips
- Proxy defaults reside in `portfolio_mcp/proxy.py`; override via `YF_PROXY` or pass `--proxy`. Avoid baking credentials into repo files.
- Audit any new MCP tools/resources for least-privilege data exposure, especially if they surface raw holdings or notes.
- Log locations (`PORTFOLIO_LOG_FILE`) may contain sensitive holdings; clean them before sharing traces.

## Commit & Pull Request Guidelines
- Git history favors short imperative subjects with a `MOD:` prefix (e.g., `MOD: add yfinance pricing`). Match that format unless maintainers change it.
- Each PR should describe the motivation, list command/test evidence (e.g., `ruff`, `pytest`), and link related issues. Include screenshots or CLI snippets when UI/CLI output changes.
- Keep diffs focused; move drive-by refactors into separate commits to ease review.
